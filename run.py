from flask import Flask, g, render_template, request, redirect, jsonify
from collections import namedtuple
import time
import sqlite3
import os


app = Flask(__name__)


def get_db():
    """Puts db connection in g if it's not there already, then returns
    that connection.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = sqlite3.connect('pastes.db')
    return g.sqlite_db


@app.teardown_appcontext
def close(e):
    """Closes db connection if it exists."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


def format_paste_filename(id):
    """Formats a paste id such that it points to the corresponding paste."""
    return os.path.join(app.root_path, 'pastes', str(id))


def write_paste(title, author, body, edit_id):
    """Writes paste metadata to the database and the body to a
    file. The id is used at a filename.
    """
    conn = get_db()
    c = conn.cursor()
    c.execute("""insert into pastes(title, author, inserted_at, edited_from)
    values (?, ?, ?, ?); """,
              (title, author, int(time.time()), edit_id))
    id = c.execute('select last_insert_rowid() from pastes').fetchone()[0]
    conn.commit()
    with open(format_paste_filename(id), 'w') as f:
        f.write(body.encode('utf-8'))
    return id


Paste = namedtuple('Paste', 'id title author inserted_at body edited_from')


def read_paste(id, read_body=True):
    """Reads a paste from an id. If read_body is False, only returns
    data from the database; otherwise, the body field of the paste is
    returned.
    """
    body = None
    if read_body:
        with open(format_paste_filename(id)) as f:
            body = unicode(f.read(), 'utf-8')
    t = get_db().cursor().execute(
        """select id, title, author, inserted_at, edited_from from pastes
        where id = ?
        """, (id,)).fetchone()
    return to_paste(t, body)


def to_paste(t, body=None):
    """Given a tuple arranged as (id, title, author, inserted_at,
    edited_from), returns a paste with body (defaults to None).
    """
    id, title, author, inserted_at, edited_from = t
    return Paste(id=id, title=title, author=author, inserted_at=inserted_at,
                 edited_from=edited_from, body=body)


def get_pastes_metadata():
    """Gets paste metadata in the form of a list of Pastes."""
    data = get_db().cursor().execute(
        'select id, title, author, inserted_at, edited_from from pastes'
    ).fetchall()
    return list(map(to_paste, data))


def lookup_forms(*names):
    """Retrieves tuple of forms from current POST request that are
    named by *names"""
    return tuple(map(lambda name: request.form[name].strip(), names))


def format_time(s):
    return time.strftime('%x %X', time.localtime(s))


def submit_page(page='home.html', edit_id=None):
    """Renders and returns a page for submitting pastes.
    Page is the filename to be rendered.
    If edit_id is not None, looks up paste with edit_id and uses it to
    fill the paste body form.
    """
    if request.method == 'POST':
        title, author, body = lookup_forms('title', 'author', 'body')
        return redirect('/pastes/' +
                        str(write_paste(title, author, body, edit_id)))
    elif edit_id:
        try:
            paste = read_paste(edit_id)
            return render_template('edit.html',
                                   title=paste.title,
                                   author=paste.author,
                                   body=paste.body)
        except IOError:
            pass
    return render_template(page)


@app.route('/', methods=['GET', 'POST'])
def home_page():
    return submit_page()


@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit_paste(id):
    return submit_page(id)


@app.route('/new', methods=['GET', 'POST'])
def new_page():
    return submit_page('edit.html')


@app.route('/search')
def search_page():
    return render_template('search.html')


@app.route('/_do_search')
def search():
    """Executes a search with the arguments title and author given in the URL.
    If both title and author are empty, all pastes are returned.
    """
    title = request.args.get('title', '').strip()
    author = request.args.get('author', '').strip()
    pastes = get_pastes_metadata()
    results = map(lambda p: (p.id,
                             format_time(p.inserted_at),
                             p.title,
                             p.author,
                             member_of_family(p, pastes)),
                  find_matches(title, author, pastes))
    return render_template("search_results.html", search_results=results)


def member_of_family(p, pastes=None):
    """ Detects if paste p is a member of family.
    If pastes is None, the value of get_pastes_metadata() is used
    """
    if pastes is None:
        pastes = get_pastes_metadata()
    return p.edited_from or any(map(lambda p2: p2.edited_from == p.id, pastes))


def find_matches(title, author, pastes):
    """Yields matches in pastes with either title or author. If title
    and author are both empty, all pastes are yielded.
    """
    everything = not author and not title
    for p in pastes:
        tmatch = title and p.title == title
        amatch = author and p.author == author
        if everything or tmatch or amatch:
            yield p


@app.route('/pastes/<id>')
def paste_page(id):
    """Reads paste from id and return page if it exists, otherwise
    return paste_not_found page.
    """
    try:
        paste = read_paste(int(id))
        return render_template('paste.html',
                               title=paste.title,
                               author=paste.author,
                               time=format_time(paste.inserted_at),
                               edited_from=paste.edited_from,
                               body=paste.body,
                               id=id,
                               family=member_of_family(paste))
    except (IOError, ValueError):
        return render_template('paste_not_found.html')


Family = namedtuple('Family', 'paste children')


@app.route('/family/<id>')
def family(id):
    """Generates family tree page from id. If id doesn't exist, returns
    paste_not_found page
    """
    try:
        id = int(id)
    except ValueError:
        return render_template('paste_not_found.html')
    family = find_family(get_pastes_metadata(), id)
    p = read_paste(id, False)
    return render_template('family.html', family=family,
                           title=p.title, id=p.id,
                           time=format_time(p.inserted_at))

def find_family(pastes_list, id):
    """ Returns the family of the oldest ancestor of paste id from pastes_list
    """
    # we can't use the id as an index to pastes_list because deleted
    # pastes might happen
    pastes = {p.id: p for p in pastes_list}
    while pastes[id].edited_from:
        id = pastes[id].edited_from

    def recur(id):
        paste = pastes[id]
        return Family(
            paste._replace(inserted_at=format_time(paste.inserted_at)),
            (recur(p.id) for p in pastes_list if p.edited_from == id))
    return recur(id)


if __name__ == '__main__':
    app.run(debug=True)
