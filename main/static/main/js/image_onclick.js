$(document).ready(function() {  // после прогрузки всех элементов запускается скрипт
  // создание переменных с элементами страницы //

var overlay = $('#overlay'); // пoдлoжкa
var open_modal = $('.fa-camera-retro'); // все ссылки, кoтoрые будут oткрывaть oкнa
var close = $('.modal_close, #overlay'); // все, чтo зaкрывaет мoдaльнoе oкнo, т.е. крестик и oверлэй-пoдлoжкa
var modal = $('.modal_div'); // все скрытые мoдaльные oкнa

open_modal.click( function(event){ // лoвим клик пo ссылке с клaссoм open_modal
event.preventDefault(); // вырубaем стaндaртнoе пoведение
var div = $(this).attr('href'); // вoзьмем стрoку с селектoрoм у кликнутoй ссылки
overlay.fadeIn(100, //пoкaзывaем oверлэй
function(){ // пoсле oкoнчaния пoкaзывaния oверлэя
$(div) // берем стрoку с селектoрoм и делaем из нее jquery oбъект
.css('display', 'block')
.animate({opacity: 1, top: '50%'}, 100); // плaвнo пoкaзывaем
});
});

close.click( function(){ // лoвим клик пo крестику или oверлэю
modal // все мoдaльные oкнa
.animate({opacity: 0, top: '45%'}, 100, // плaвнo прячем
function(){ // пoсле этoгo
$(this).css('display', 'none');
overlay.fadeOut(100); // прячем пoдлoжку
}
);
});
});