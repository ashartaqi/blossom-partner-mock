/* Inline stroke icons.
 *
 * Hand-written rather than pulled from a library: the app needs eleven glyphs,
 * and a dependency for that would outweigh the icons. All 24x24, all
 * currentColor, so a single `color` on the parent styles them. */

function Icon({ children, ...rest }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const IconHome = (props) => (
  <Icon {...props}>
    <path d="M3 10.2 12 3l9 7.2" />
    <path d="M5 9.5V20a1 1 0 0 0 1 1h3.5v-5.5h5V21H18a1 1 0 0 0 1-1V9.5" />
  </Icon>
);

export const IconMoney = (props) => (
  <Icon {...props}>
    <rect x="2.5" y="6" width="19" height="12" rx="2.5" />
    <circle cx="12" cy="12" r="2.6" />
    <path d="M6 10v4M18 10v4" />
  </Icon>
);

export const IconMoveMoney = (props) => (
  <Icon {...props}>
    <path d="M4 8h13M14 5l3 3-3 3" />
    <path d="M20 16H7M10 13l-3 3 3 3" />
  </Icon>
);

export const IconInvestments = (props) => (
  <Icon {...props}>
    <path d="M3 20h18" />
    <path d="M6 20v-6M11 20V8M16 20v-9M21 20V5" />
  </Icon>
);

/* Services is a directory of things, so: a grid. The cog belongs to Settings,
 * and two cogs in one chrome would be two different meanings on one glyph. */
export const IconServices = (props) => (
  <Icon {...props}>
    <rect x="3.5" y="3.5" width="7" height="7" rx="1.8" />
    <rect x="13.5" y="3.5" width="7" height="7" rx="1.8" />
    <rect x="3.5" y="13.5" width="7" height="7" rx="1.8" />
    <rect x="13.5" y="13.5" width="7" height="7" rx="1.8" />
  </Icon>
);

export const IconStatements = (props) => (
  <Icon {...props}>
    <path d="M6 2.5h8L19 8v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1Z" />
    <path d="M13.5 2.8V8H19" />
    <path d="M8.5 13h7M8.5 17h4.5" />
  </Icon>
);

export const IconMessages = (props) => (
  <Icon {...props}>
    <path d="M21 12a8 8 0 0 1-8 8H4l1.6-3.2A8 8 0 1 1 21 12Z" />
  </Icon>
);

export const IconSignOut = (props) => (
  <Icon {...props}>
    <path d="M14 20H6a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h8" />
    <path d="M17 15.5 20.5 12 17 8.5M20 12H10" />
  </Icon>
);

export const IconSettings = (props) => (
  <Icon {...props}>
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1v.3a2 2 0 1 1-4 0v-.2a1.6 1.6 0 0 0-2.8-1.1l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 3.5 15H3a2 2 0 1 1 0-4h.2A1.6 1.6 0 0 0 4.3 8.2l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.6 1.6 0 0 0 9.9 4.3V4a2 2 0 1 1 4 0v.2a1.6 1.6 0 0 0 2.7 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0 1.1 2.7h.3a2 2 0 1 1 0 4h-.2a1.6 1.6 0 0 0-1.2 1.2Z" />
  </Icon>
);

export const IconBell = (props) => (
  <Icon {...props}>
    <path d="M18 9a6 6 0 1 0-12 0c0 5-2 6.5-2 6.5h16S18 14 18 9Z" />
    <path d="M13.7 19a2 2 0 0 1-3.4 0" />
  </Icon>
);

export const IconSearch = (props) => (
  <Icon {...props}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="m20 20-4.2-4.2" />
  </Icon>
);

export const IconEye = (props) => (
  <Icon {...props}>
    <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
    <circle cx="12" cy="12" r="3" />
  </Icon>
);

export const IconEyeOff = (props) => (
  <Icon {...props}>
    <path d="M10 5.7a7.7 7.7 0 0 1 2-.2c6 0 9.5 6.5 9.5 6.5a16 16 0 0 1-2.9 3.7" />
    <path d="M6.5 6.9A16 16 0 0 0 2.5 12S6 18.5 12 18.5c1.6 0 3-.5 4.2-1.1" />
    <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
    <path d="m3.5 3.5 17 17" />
  </Icon>
);

export const IconCode = (props) => (
  <Icon {...props}>
    <path d="m8.5 8-4.5 4 4.5 4M15.5 8l4.5 4-4.5 4" />
  </Icon>
);

export const IconUser = (props) => (
  <Icon {...props}>
    <circle cx="12" cy="8" r="3.8" />
    <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
  </Icon>
);

export const IconChevronDown = (props) => (
  <Icon {...props}>
    <path d="m6 9 6 6 6-6" />
  </Icon>
);
