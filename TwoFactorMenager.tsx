import React, { useEffect, useMemo, useRef, useState } from "react";

/**
 * Minimalny kontrakt API po stronie backendu (przykład):
 * GET    /api/2fa/status           -> { enabled: boolean }
 * POST   /api/2fa/setup            -> { otpauthUrl: string, secret: string }
 * POST   /api/2fa/enable           body: { code: string } -> { ok: true }
 * POST   /api/2fa/disable          body: { code: string } -> { ok: true }
 * (opcjonalnie) GET /api/2fa/qr?otpauth=<urlencoded otpauth>
 *  - generuje obrazek QR (image/png or image/svg+xml) dla otpauthUrl
 */

type StatusRes = { enabled: boolean };
type SetupRes = { otpauthUrl: string; secret: string };
type MutateRes = { ok: boolean; message?: string };

const fetchJSON = async <T,>(
  input: RequestInfo,
  init?: RequestInit
): Promise<T> => {
  const res = await fetch(input, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
};

const isSixDigits = (v: string) => /^[0-9]{6}$/.test(v.trim());

export default function TwoFactorManager() {
  const [loading, setLoading] = useState(true);
  const [enabled, setEnabled] = useState<boolean | null>(null);

  // Stan "setup" (gdy użytkownik włącza 2FA)
  const [otpauthUrl, setOtpauthUrl] = useState<string>("");
  const [secret, setSecret] = useState<string>("");

  // Weryfikacja kodu (zarówno enable jak i disable)
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const codeInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const data = await fetchJSON<StatusRes>("/api/2fa/status");
        if (!mounted) return;
        setEnabled(data.enabled);
      } catch (e: any) {
        setError(e?.message ?? "Nie udało się pobrać statusu 2FA.");
      } finally {
        setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  // Rozpocznij setup (pobierz otpauth + secret + pokaż QR)
  const beginSetup = async () => {
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      const data = await fetchJSON<SetupRes>("/api/2fa/setup", { method: "POST" });
      setOtpauthUrl(data.otpauthUrl);
      setSecret(data.secret);
      // Skup od razu pole kodu
      setTimeout(() => codeInputRef.current?.focus(), 0);
    } catch (e: any) {
      setError(e?.message ?? "Nie udało się zainicjować 2FA.");
    } finally {
      setSubmitting(false);
    }
  };

  // Zatwierdź włączenie 2FA (weryfikacja kodu)
  const confirmEnable = async () => {
    setError(null);
    setSuccess(null);
    if (!isSixDigits(code)) {
      setError("Wpisz 6-cyfrowy kod z aplikacji 2FA.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetchJSON<MutateRes>("/api/2fa/enable", {
        method: "POST",
        body: JSON.stringify({ code }),
      });
      if (res.ok) {
        setEnabled(true);
        setSuccess("2FA zostało włączone.");
        setOtpauthUrl("");
        setSecret("");
        setCode("");
      } else {
        setError(res.message || "Nie udało się włączyć 2FA.");
      }
    } catch (e: any) {
      setError(e?.message ?? "Nie udało się włączyć 2FA.");
    } finally {
      setSubmitting(false);
    }
  };

  // Wyłącz 2FA (z potwierdzeniem kodem z aplikacji)
  const disable2FA = async () => {
    setError(null);
    setSuccess(null);
    if (!isSixDigits(code)) {
      setError("Wpisz 6-cyfrowy kod z aplikacji 2FA.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetchJSON<MutateRes>("/api/2fa/disable", {
        method: "POST",
        body: JSON.stringify({ code }),
      });
      if (res.ok) {
        setEnabled(false);
        setSuccess("2FA zostało wyłączone.");
        setCode("");
      } else {
        setError(res.message || "Nie udało się wyłączyć 2FA.");
      }
    } catch (e: any) {
      setError(e?.message ?? "Nie udało się wyłączyć 2FA.");
    } finally {
      setSubmitting(false);
    }
  };

  // Źródło obrazka QR:
  // 1) preferowany backend: /api/2fa/qr?otpauth=...
  // 2) fallback dev: publiczny generator (uwaga na prywatność w produkcji!)
  const qrSrc = useMemo(() => {
    if (!otpauthUrl) return "";
    const backendQR = `/api/2fa/qr?otpauth=${encodeURIComponent(otpauthUrl)}`;
    const fallbackQR = `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodeURIComponent(
      otpauthUrl
    )}`;
    // Jeśli Twój backend ma endpoint, użyj jego; inaczej fallback.
    return backendQR;
    // return fallbackQR;
  }, [otpauthUrl]);

  if (loading) {
    return (
      <Section>
        <Header t="Dwuskładnikowe uwierzytelnianie (2FA)" />
        <p>Ładowanie…</p>
      </Section>
    );
  }

  return (
    <Section>
      <Header t="Dwuskładnikowe uwierzytelnianie (2FA)" />
      <StatusPill enabled={!!enabled} />

      {error && <Alert type="error" msg={error} onClose={() => setError(null)} />}
      {success && (
        <Alert type="success" msg={success} onClose={() => setSuccess(null)} />
      )}

      {/* Gdy 2FA WYŁĄCZONE – pokaż CTA włączenia */}
      {enabled === false && !otpauthUrl && (
        <Card>
          <h3>Chroń konto kodami z aplikacji (TOTP)</h3>
          <p>
            Do włączenia użyj dowolnej aplikacji 2FA (np. Google Authenticator,
            1Password, Authy). Zeskanuj kod QR, wpisz 6-cyfrowy kod i gotowe.
          </p>
          <div className="actions">
            <button
              className="btn primary"
              onClick={beginSetup}
              disabled={submitting}
            >
              {submitting ? "Przygotowywanie…" : "Włącz 2FA"}
            </button>
          </div>
        </Card>
      )}

      {/* Ekran konfiguracji: QR + secret + pole kodu */}
      {enabled === false && otpauthUrl && (
        <Card>
          <h3>Krok 1/2 — zeskanuj kod QR</h3>
          <div className="qrRow">
            <img
              src={qrSrc}
              alt="Kod QR do skonfigurowania 2FA w aplikacji"
              width={240}
              height={240}
              style={{ imageRendering: "pixelated" }}
            />
            <div className="qrHelp">
              <details>
                <summary>Nie możesz zeskanować?</summary>
                <code className="secret" aria-label="Sekretny klucz TOTP">
                  {secret}
                </code>
                <p>
                  W aplikacji wybierz „Wpisz klucz ręcznie” i podaj powyższy
                  sekret.
                </p>
              </details>
              <p className="muted">
                Upewnij się, że czas na urządzeniu jest poprawny (TOTP używa czasu
                systemowego).
              </p>
            </div>
          </div>

          <h3>Krok 2/2 — potwierdź kod</h3>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!submitting) confirmEnable();
            }}
          >
            <label htmlFor="totp">Kod z aplikacji (6 cyfr)</label>
            <input
              id="totp"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]*"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              ref={codeInputRef}
              placeholder="••••••"
              aria-invalid={!!error && !isSixDigits(code)}
            />
            <div className="actions">
              <button
                type="submit"
                className="btn primary"
                disabled={submitting || !isSixDigits(code)}
              >
                {submitting ? "Włączanie…" : "Potwierdź i włącz"}
              </button>
              <button
                type="button"
                className="btn ghost"
                disabled={submitting}
                onClick={() => {
                  setOtpauthUrl("");
                  setSecret("");
                  setCode("");
                  setError(null);
                }}
              >
                Anuluj
              </button>
            </div>
          </form>
        </Card>
      )}

      {/* Gdy 2FA WŁĄCZONE – możliwość wyłączenia (z kodem) */}
      {enabled === true && (
        <Card>
          <h3>Wyłącz 2FA</h3>
          <p className="muted">
            Aby wyłączyć, podaj aktualny 6-cyfrowy kod z aplikacji 2FA.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!submitting) disable2FA();
            }}
          >
            <label htmlFor="totp-off">Kod z aplikacji (6 cyfr)</label>
            <input
              id="totp-off"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]*"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              placeholder="••••••"
            />
            <div className="actions">
              <button
                type="submit"
                className="btn danger"
                disabled={submitting || !isSixDigits(code)}
              >
                {submitting ? "Wyłączanie…" : "Wyłącz 2FA"}
              </button>
            </div>
          </form>
        </Card>
      )}

      <SmallPrint />
      <Styles />
    </Section>
  );
}

/* —————— POMOCNICZE KOMPONENTY UI —————— */

function Section({ children }: { children: React.ReactNode }) {
  return <section className="twofa">{children}</section>;
}
function Header({ t }: { t: string }) {
  return (
    <div className="header">
      <h2>{t}</h2>
    </div>
  );
}
function StatusPill({ enabled }: { enabled: boolean }) {
  return (
    <div
      className={`pill ${enabled ? "on" : "off"}`}
      role="status"
      aria-live="polite"
    >
      {enabled ? "Włączone" : "Wyłączone"}
    </div>
  );
}
function Card({ children }: { children: React.ReactNode }) {
  return <div className="card">{children}</div>;
}
function Alert({
  type,
  msg,
  onClose,
}: {
  type: "error" | "success";
  msg: string;
  onClose?: () => void;
}) {
  return (
    <div className={`alert ${type}`} role="alert">
      <span>{msg}</span>
      {onClose && (
        <button className="x" aria-label="Zamknij" onClick={onClose}>
          ×
        </button>
      )}
    </div>
  );
}
function SmallPrint() {
  return (
    <p className="tiny">
      Wskazówka: w produkcji generuj obraz QR po swojej stronie backendu (nie
      wysyłaj sekretnych danych do usług trzecich). Nie loguj kodów TOTP ani
      secretu. Rozważ dodanie jednorazowych kodów awaryjnych.
    </p>
  );
}
function Styles() {
  return (
    <style>{`
.twofa { max-width: 720px; margin: 0 auto; font-family: ui-sans-serif, system-ui, -apple-system; }
.header { display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px; }
.pill { display:inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.pill.on { background: #ecfdf5; color:#065f46; border:1px solid #a7f3d0; }
.pill.off { background: #fef2f2; color:#991b1b; border:1px solid #fecaca; }
.card { border:1px solid #e5e7eb; border-radius: 12px; padding: 16px; margin-top: 12px; }
.card h3 { margin: 0 0 8px; font-size: 16px; }
.alert { display:flex; justify-content:space-between; gap:12px; align-items:center; padding:10px 12px; border-radius: 10px; margin: 10px 0; font-size:14px; }
.alert.error { background:#fef2f2; color:#7f1d1d; border:1px solid #fecaca; }
.alert.success { background:#f0fdf4; color:#065f46; border:1px solid #bbf7d0; }
.alert .x { background:transparent; border:none; font-size:18px; line-height:1; cursor:pointer; color:inherit; }
label { display:block; font-weight:600; margin-top: 8px; margin-bottom:6px; }
input[type="text"], input[type="number"], input[type="password"] {
  border:1px solid #d1d5db; border-radius:10px; padding:10px 12px; font-size:16px; width: 220px;
}
input#totp, input#totp-off { letter-spacing: 6px; text-align:center; font-weight:700; width: 160px; }
.actions { display:flex; gap:10px; margin-top:12px; }
.btn { border:1px solid #d1d5db; background:#fff; padding:10px 14px; border-radius:10px; cursor:pointer; font-weight:600; }
.btn.primary { background:#111827; color:#fff; border-color:#111827; }
.btn.primary:disabled, .btn.danger:disabled { opacity:.6; cursor:not-allowed; }
.btn.ghost { background:transparent; }
.btn.danger { background:#b91c1c; color:#fff; border-color:#b91c1c; }
.muted { color:#6b7280; }
.qrRow { display:flex; gap:16px; align-items:flex-start; }
.qrHelp details { margin-bottom:8px; }
.secret { display:inline-block; margin-top:6px; padding:6px 8px; border-radius:6px; background:#111827; color:#fff; user-select:all; }
.tiny { margin-top: 16px; color:#6b7280; font-size:12px; }
@media (max-width: 600px) {
  .qrRow { flex-direction:column; }
}
    `}</style>
  );
}