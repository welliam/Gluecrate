var Family = (function () {
    function render_family(family) {
        var p = family.paste
        return Common.format_result(p.id, p.title, p.author, p.inserted_at) 
            + '<ul>'
            + family.children.map(render_family).join('')
            + '</ul>'
    }

    return {
        render_to_contents: function(f) {
            $('#results').append(render_family(f))
        }
    }
})()
