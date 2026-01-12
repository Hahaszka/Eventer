$(document).ready(function () {
  const $loader = $("#globalLoader");
  $(document).ajaxStart(function () {
    $loader.removeClass("d-none").stop(true, true).fadeIn(200);
  });
  $(document).ajaxStop(function () {
    $loader.stop(true, true).fadeOut(200, function () {
      $(this).addClass("d-none");
    });
  });
});
