import { useId, useState } from "react";

import { IconEye, IconEyeOff } from "./icons";

/** A filled field whose label sits inside it and floats up once there is a value.
 *
 *  Mirrors the investing app's input, so the two products' forms feel like one
 *  product. The float is pure CSS — the input carries a single-space placeholder
 *  so `:placeholder-shown` can stand in for "is empty", which also catches
 *  browser autofill, where no React state change ever fires. */
export default function FloatingInput({
  label,
  error,
  hint,
  type = "text",
  id: idProp,
  ...rest
}) {
  const generatedId = useId();
  const id = idProp ?? generatedId;
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;

  const [revealed, setRevealed] = useState(false);
  const isPassword = type === "password";
  const inputType = isPassword && revealed ? "text" : type;

  return (
    <div className="field">
      <div className={`field-box${error ? " has-error" : ""}`}>
        {/* Before the label in the DOM, so the sibling selectors can reach it. */}
        <input
          id={id}
          type={inputType}
          placeholder=" "
          aria-invalid={error ? "true" : undefined}
          aria-describedby={[errorId, hintId].filter(Boolean).join(" ") || undefined}
          className={isPassword ? "field-input has-trailing" : "field-input"}
          {...rest}
        />
        <label htmlFor={id} className="field-label">
          {label}
        </label>

        {isPassword && (
          <button
            type="button"
            className="field-trailing"
            onClick={() => setRevealed((v) => !v)}
            aria-label={revealed ? "Hide password" : "Show password"}
          >
            {revealed ? <IconEyeOff /> : <IconEye />}
          </button>
        )}
      </div>

      {error ? (
        <p id={errorId} className="field-error">
          {error}
        </p>
      ) : (
        hint && (
          <p id={hintId} className="field-hint">
            {hint}
          </p>
        )
      )}
    </div>
  );
}
