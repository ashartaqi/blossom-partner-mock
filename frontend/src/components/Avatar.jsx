import { useState } from "react";

function initials(user) {
  const letters = `${user?.first_name?.[0] ?? ""}${user?.last_name?.[0] ?? ""}`;
  return letters.toUpperCase() || user?.email?.[0]?.toUpperCase() || "?";
}

/** The member's picture, assigned once at signup and served by an external
 *  avatar service.
 *
 *  Falls back to initials if the image fails to load. That is not defensive
 *  padding: the picture comes from a third-party host, and an offline laptop or
 *  a blocked request would otherwise leave a broken-image glyph in the header. */
export default function Avatar({ user, className = "", size }) {
  const [failed, setFailed] = useState(false);
  const src = user?.picture;
  const style = size ? { width: size, height: size } : undefined;

  if (!src || failed) {
    return (
      <span className={`avatar avatar-fallback ${className}`} style={style} aria-hidden="true">
        {initials(user)}
      </span>
    );
  }

  return (
    <img
      className={`avatar ${className}`}
      style={style}
      src={src}
      alt=""
      onError={() => setFailed(true)}
    />
  );
}
