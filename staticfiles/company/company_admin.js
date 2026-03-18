// This file will contain custom JavaScript for the Company admin
(function($) {
    $(document).ready(function() {
        // Change 'id_no_of_employees' if your field's id is different
        $('#id_no_of_employees').change(function() {
            alert('Number of employees changed!');
        });
    });
})(django.jQuery);
