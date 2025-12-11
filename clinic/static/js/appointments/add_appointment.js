// Select2 custom matcher for searching any part of patient name or phone
function matchCustom(params, data) {
    if ($.trim(params.term) === '') {
        return data;
    }

    if (typeof data.text === 'undefined') {
        return null;
    }

    // Case-insensitive search
    if (data.text.toLowerCase().indexOf(params.term.toLowerCase()) > -1) {
        return data;
    }

    return null;
}

$(document).ready(function () {
    $('#patientSelect').select2({
        placeholder: "Search patient by name or phone",
        allowClear: true,
        width: '100%',
        matcher: matchCustom
    });
});
