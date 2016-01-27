(function() {

    function add_matches(matches) {
        matches = matches['items']
        resultslist = $("#results").text("")
        if (matches.length == 0) {
            resultslist.append("No results!");
            return;
        }

        for (var e of matches) {
            var title = process_metadatum(e['title']),
                author = process_metadatum(e['author']),
                time = e['inserted_at']

            resultslist.append(
                '<li><a href="pastes/' + e['id'] + '">'
                    + (title ? title : '')
                    + (author ? ' by ' + author : '')
                    + (title || author ? ' on ' : '')
                    + time
                    + '</a></li>'
            )
        }
    }

    var tagsToReplace = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;'
    };

    function escape_tags(str) {
        return str.replace(/[&<>]/g, function(t) {
            return tagsToReplace[t] || t;
        })
    }

    function process_metadatum(s) {
        return s.length > 0 && escape_tags(s)
    }

    $(document).ready(function() {
        $('#searchform').submit(function (event) {
            $.getJSON('/_do_search', {
                title: $('input[name="title"]').val(),
                author: $('input[name="author"]').val()
            }, add_matches)
            event.preventDefault()
            // $.put({author: author}
        })
    });

})();
