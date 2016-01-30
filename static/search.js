(function() {
    function form_searcher(formid, url, get_data) {
        $(formid).submit(function (event) {
            $.get('/_do_search', get_data(), function (data) {
                $("#results").html(data)
            })
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
