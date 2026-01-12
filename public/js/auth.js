$(document).ready(function () {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("error") === "access_denied") {
    $("#alertBox")
      .text("Anulowano logowanie przez Google.")
      .removeClass("d-none");

    window.history.replaceState({}, document.title, window.location.pathname);
  }
  let isLoginView = true;

  const $loginForm = $("#loginForm");
  const $registerForm = $("#registerForm");
  const $toggleBtn = $("#toggleModeBtn");
  const $toggleText = $("#toggleText");
  const $headerText = $("#headerText");
  const $alertBox = $("#alertBox");
  const $successBox = $("#successBox");

  // === 1. PRZEŁĄCZANIE WIDOKÓW ===
  $toggleBtn.click(function (e) {
    e.preventDefault();
    clearAlerts();

    if (isLoginView) {
      // Przełącz na Rejestrację
      $loginForm.addClass("d-none");
      $registerForm.removeClass("d-none").addClass("fade-in");

      $headerText.text("Dołącz do Eventer. Stwórz darmowe konto.");
      $toggleText.text("Masz już konto?");
      $(this).text("Zaloguj się");
    } else {
      // Przełącz na Logowanie
      $registerForm.addClass("d-none");
      $loginForm.removeClass("d-none").addClass("fade-in");

      $headerText.text("Witaj ponownie. Zaloguj się, aby kontynuować.");
      $toggleText.text("Nie masz jeszcze konta?");
      $(this).text("Zarejestruj się");
    }
    isLoginView = !isLoginView;
  });

  // === 2. OBSŁUGA LOGOWANIA ===
  $loginForm.submit(function (e) {
    e.preventDefault();
    clearAlerts();
    const $btn = $(this).find("button");
    loading($btn, true);

    const formData = $(this).serialize();

    $.ajax({
      url: "/auth/jwt/login",
      method: "POST",
      data: formData,
      contentType: "application/x-www-form-urlencoded",
      success: function (response) {
        localStorage.setItem("eventer_token", response.access_token);
        window.location.href = "/dashboard.html";
      },
      error: function (xhr) {
        showError("Nieprawidłowy email lub hasło.");
        loading($btn, false);
      },
    });
  });

  // === 3. OBSŁUGA REJESTRACJI ===
  $registerForm.submit(function (e) {
    e.preventDefault();
    clearAlerts();

    const email = $("#regEmail").val();
    const password = $("#regPassword").val();
    const confirm = $("#regPasswordConfirm").val();
    const $btn = $(this).find("button");

    if (password !== confirm) {
      showError("Hasła nie są identyczne.");
      return;
    }

    if (password.length < 6) {
      showError("Hasło jest za krótkie.");
      return;
    }

    loading($btn, true);

    const payload = JSON.stringify({
      email: email,
      password: password,
      is_active: true,
      is_superuser: false,
      is_verified: false,
    });

    $.ajax({
      url: "/auth/register",
      method: "POST",
      data: payload,
      contentType: "application/json",
      success: function (response) {
        $successBox
          .text("Konto utworzone pomyślnie! Możesz się teraz zalogować.")
          .removeClass("d-none");
        $registerForm[0].reset();

        setTimeout(() => {
          $toggleBtn.click();
        }, 2000);
      },
      error: function (xhr) {
        let msg = "Wystąpił błąd rejestracji.";
        if (xhr.responseJSON && xhr.responseJSON.detail) {
          msg = xhr.responseJSON.detail;
        }
        showError(msg);
      },
      complete: function () {
        loading($btn, false);
      },
    });
  });

  // === 4. GOOGLE AUTH ===
  $("#googleBtn").click(function (e) {
    e.preventDefault();
    $.ajax({
      url: "/auth/google/authorize",
      method: "GET",
      success: function (response) {
        window.location.href = response.authorization_url;
      },
      error: function (xhr) {
        console.error("Błąd pobierania linku Google Auth", xhr);
        alert("Nie udało się połączyć z Google. Sprawdź konsolę.");
      },
    });
  });

  function showError(msg) {
    $alertBox.text(msg).removeClass("d-none");
  }

  function clearAlerts() {
    $alertBox.addClass("d-none");
    $successBox.addClass("d-none");
  }

  function loading($btn, isLoading) {
    if (isLoading) {
      $btn.data("original-text", $btn.text());
      $btn.prop("disabled", true).text("Przetwarzanie...");
    } else {
      $btn.prop("disabled", false).text($btn.data("original-text"));
    }
  }
});
