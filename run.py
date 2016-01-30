from flask import Flask, g, render_template, request, redirect, jsonify
import time
from collections import namedtuple
import sqlite3
import os


app = Flask(__name__)


def get_db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = sqlite3.connect('pastes.db')
    return g.sqlite_db


@app.teardown_appcontext
def close(e):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


def format_paste_filename(id):
    return os.path.join(app.root_path, 'pastes', str(id))


def write_paste(title, author, body, edit_id):
    conn = get_db()
    c = conn.cursor()

    c.execute('''insert into pastes(title, author, inserted_at, edited_from)
    values (?, ?, ?, ?); ''',
              (title, author, int(time.time()), edit_id))
    id = c.execute('select last_insert_rowid() from pastes').fetchone()[0]
    conn.commit()
    with open(format_paste_filename(id), 'w') as f:
        f.write(body.encode('utf-8'))
    return id


Paste = namedtuple('Paste', 'id title author inserted_at body edited_from')


def read_paste(id, read_body=True):
    body = None
    if read_body:
        with open(format_paste_filename(id)) as f:
            body = unicode(f.read(), 'utf-8')

    title, author, inserted_at, edited_from = get_db().cursor().execute(
        '''
        select title, author, inserted_at, edited_from from pastes where id = ?
        ''', (id,)).fetchone()

    return Paste(id=id, title=title, author=author, inserted_at=inserted_at,
                 edited_from=edited_from, body=body)


def read_all_pastes(read_body=False):
    return (read_paste(int(id), read_body=read_body)
            for id in os.listdir('pastes'))


def to_paste(t):
    id, title, author, inserted_at, edited_from = t
    return Paste(id=id, title=title, author=author, inserted_at=inserted_at,
                 edited_from=edited_from, body=None)


def get_pastes_metadata():
    data = get_db().cursor().execute(
        'select id, title, author, inserted_at, edited_from from pastes'
    ).fetchall()
    return list(map(to_paste, data))


def lookup_forms(*names):
    return tuple(map(lambda name: request.form[name].strip(), names))


def format_time(s):
    return time.strftime('%x %X', time.localtime(s))


def submit_page(edit_id=None):
    if request.method == 'POST':
        title, author, body = lookup_forms('title', 'author', 'body')
        return redirect('/pastes/' +
                        str(write_paste(title, author, body, edit_id)))
    else:
        paste = None
        if edit_id:
            try:
                paste = read_paste(edit_id)
            except IOError:
                pass
        return render_template('submit.html',
                               title=paste and paste.title,
                               author=paste and paste.author,
                               body=paste and paste.body)


@app.route('/', methods=['GET', 'POST'])
def home_page():
    return submit_page()


@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit_paste(id):
    return submit_page(id)


@app.route('/search')
def search_page():
    return render_template('search.html')


@app.route('/_do_search')
def search():
    title = request.args.get('title', '')
    author = request.args.get('author', '')
    pastes = get_pastes_metadata()
    results = map(lambda p: (p.id,
                             format_time(p.inserted_at),
                             p.title,
                             p.author,
                             member_of_family(p, pastes)),
                  find_matches(title, author, pastes))
    return render_template("search_results.html", search_results=results)


def member_of_family(p, pastes=None):
    pastes = pastes or get_pastes_metadata()
    return p.edited_from or any(map(lambda p2: p2.edited_from == p.id, pastes))


def find_matches(title, author, pastes):
    everything = not author and not title
    for p in pastes:
        tmatch = title and p[1] == title
        amatch = author and p[2] == author
        if everything or tmatch or amatch:
            yield p


@app.route('/pastes/<id>')
def paste_page(id):
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
    try:
        id = int(id)
    except (ValueError, IOError):
        return render_template('paste_not_found.html')
    family = find_family(get_pastes_metadata(), id)
    return render_template('family.html', family=family, id=id)


def find_family(glues_list, id):
    # we can't use the id as an index to glues_list because deleted
    # pastes might happen
    glues = {p.id: p for p in glues_list}
    og = id  # OG stands for Original Glue
    while glues[og].edited_from:
        og = glues[id].edited_from

    def recur(id):
        return Family(glues[id],
                      (recur(p.id) for p in glues_list
                       if p.edited_from == id))
    return recur(og)


if __name__ == '__main__':
    app.run(debug=True)
