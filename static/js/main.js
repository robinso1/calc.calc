$(document).ready(function() {
    $('#calculateButton').on('click', function() {
        const formData = {
            length: $('#length').val(),
            width: $('#width').val(),
            depth: $('#depth').val()
        };

        $.ajax({
            url: '/calculate',
            type: 'POST',
            data: formData,
            success: function(response) {
                const resultDiv = $('#result');
                resultDiv.show();
                
                if (response.success) {
                    resultDiv.html(`<p>${response.message}</p>`);
                    resultDiv.removeClass('error');
                } else {
                    resultDiv.html(`<p>Ошибка: ${response.message}</p>`);
                    resultDiv.addClass('error');
                }
            },
            error: function(xhr, status, error) {
                const resultDiv = $('#result');
                resultDiv.show();
                resultDiv.html('<p>Произошла ошибка при отправке запроса</p>');
                resultDiv.addClass('error');
                console.error('Ошибка:', error);
            }
        });
    });
});
