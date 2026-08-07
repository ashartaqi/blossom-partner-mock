import {
  IconCode,
  IconHome,
  IconInvestments,
  IconMessages,
  IconMoney,
  IconMoveMoney,
  IconServices,
  IconStatements,
  IconUser,
} from "./icons";

/* The investing app is not a route in this app — it is another product on
 * another origin. So it is an absolute href, and the sidebar renders it as a
 * plain anchor rather than a router Link.
 *
 * Not a fetch, either. A fetch would be blocked cross-origin, could not follow
 * the redirect chain, and could not carry the cookie the hand-off depends on.
 * Only a real navigation does all three. */
export const INVESTMENTS_URL =
  import.meta.env.VITE_INVESTMENTS_URL ??
  "http://localhost:8000/api/sso/blossom/start/";

/* Mirrors the investing app's own rail, so a member crossing between the two
 * meets the same furniture in the same places. The items with `href: "#"` are
 * scenery — this is a mock of a banking platform, not a banking platform. */
export const SIDEBAR_SECTIONS = [
  {
    items: [
      { id: "dashboard", label: "Home", icon: IconHome, to: "/dashboard" },
      { id: "money", label: "Money", icon: IconMoney, to: "/money" },
      { id: "move-money", label: "Move Money", icon: IconMoveMoney, to: "#" },
      {
        id: "investments",
        label: "Investments",
        icon: IconInvestments,
        href: INVESTMENTS_URL,
      },
      { id: "services", label: "Services", icon: IconServices, to: "#" },
    ],
  },
  {
    label: "Quick access",
    items: [
      { id: "statements", label: "Statements", icon: IconStatements, to: "#" },
      { id: "messages", label: "Messages", icon: IconMessages, to: "#" },
      { id: "profile", label: "Profile", icon: IconUser, to: "/profile" },
    ],
  },
  {
    // Nothing a member would ever open. It lives in the app rather than in a
    // document because it reads the running configuration, and a document about
    // configuration is wrong the moment someone changes it.
    label: "For developers",
    items: [
      {
        id: "developer",
        label: "Integration",
        icon: IconCode,
        to: "/developer",
      },
    ],
  },
];

/** Shown on mobile, where the rail is off-screen. */
export const BOTTOM_NAV_ITEMS = [
  { id: "dashboard", label: "Home", icon: IconHome, to: "/dashboard" },
  { id: "money", label: "Money", icon: IconMoney, to: "/money" },
  {
    id: "investments",
    label: "Investments",
    icon: IconInvestments,
    href: INVESTMENTS_URL,
  },
  { id: "profile", label: "Profile", icon: IconUser, to: "/profile" },
];
