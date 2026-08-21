import { useEffect, useState } from "react";

/** A value that exists to be handed to somebody else, with a button that does it.
 *
 *  These get pasted into another team's configuration, and a URL transcribed by
 *  eye is a URL with a typo in it — an issuer that is one character off fails ID
 *  token validation with an error that says nothing about spelling. */
export default function CopyField({ label, value }) {
  const [copied, setCopied] = useState(false);

  // Reset the label a moment after copying, so the button does not sit there
  // claiming "Copied" for the rest of the session.
  useEffect(() => {
    if (!copied) return undefined;
    const timer = setTimeout(() => setCopied(false), 1600);
    return () => clearTimeout(timer);
  }, [copied]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
    } catch {
      // Clipboard access can be refused (insecure origin, denied permission).
      // The value is selectable either way, so there is nothing to recover from.
    }
  }

  return (
    <div className="copy-field">
      <span className="copy-label">{label}</span>
      <div className="copy-row">
        <code className="copy-value">{value}</code>
        <button type="button" className="copy-btn" onClick={copy}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
    </div>
  );
}
