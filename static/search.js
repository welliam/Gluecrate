(function() {
    function add_matches(matches) {
        matches = matches['matches']
        resultslist = $("#results").text("")
        if (matches.length == 0) {
            resultslist.append("No results!");
            return;
        }

        for (var e of matches) {
            var title = process_metadatum(e['title']),
                author = process_metadatum(e['author']),
                time = e['inserted_at']
                id = e['id']

            resultslist.append(Common.format_result(id, title, author, time, true))
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

    function form_searcher(formid, jsonurl, get_data) {
        $(formid).submit(function (event) {
            $.getJSON(jsonurl, get_data(), add_matches)
            event.preventDefault()
        })
    }

    $(document).ready(function() {
        form_searcher('#searchform', '/_do_search', function () {
            return {
                title: $('input[name="title"]').val(),
                author: $('input[name="author"]').val()
            }
        })
    })
})()
