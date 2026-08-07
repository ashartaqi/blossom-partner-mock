/** The frame both auth screens sit in.
 *
 *  A full-height centred column rather than a floating card, matching the
 *  investing app: a member who signs in on one side and is handed to the other
 *  should not feel the seam. The actions sit in their own block at the foot, so
 *  the submit button lands in the same place on both screens regardless of how
 *  many fields are above it. */
export default function AuthLayout({ title, description, children, footer }) {
  return (
    <div className="auth">
      <div className="auth-column">
        <div className="auth-top">
          <span className="auth-brand">
            <span className="brand-mark" aria-hidden="true">
              B
            </span>
            Blossom
          </span>
          <div className="auth-heading">
            <h1>{title}</h1>
            <p>{description}</p>
          </div>
        </div>

        {children}

        <div className="auth-foot">{footer}</div>
      </div>
    </div>
  );
}
