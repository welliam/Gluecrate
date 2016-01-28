var Common = {
    format_result: function (id, title, author, time, family) {
        return '<li><a href="/pastes/' + id + '">'
            + (title ? title : '')
            + (author ? ' by ' + author : '')
            + (title || author ? ' on ' : '')
            + time
            + '</a> (<a href=/edit/' + id + '>edit</a>'
            + (family ? (', <a href=/family/' + id + '>family</a>') : '')
            + ')</li>'
    }
}
