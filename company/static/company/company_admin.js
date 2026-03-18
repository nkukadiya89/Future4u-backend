// This file will contain custom JavaScript for the Company admin
(function() {
    function runWhenReady() {
        if (typeof django !== "undefined" && typeof django.jQuery !== "undefined") {
            (function($) {
                $(document).ready(function() {
                    $('#id_no_of_employees').change(function() {
                        alert('Number of employees changed!');
                    });
                });
            })(django.jQuery);
        } else {
            setTimeout(runWhenReady, 50);
        }
    }
    runWhenReady();
})();
