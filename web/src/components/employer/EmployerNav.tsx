"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ChartIcon,
  ColumnsIcon,
  GearIcon,
  InboxIcon,
  ListIcon,
  PlusIcon,
} from "@/components/icons";

const ITEMS = [
  { href: "/employer", label: "Overview", icon: ChartIcon, exact: true },
  { href: "/employer/post", label: "Post a Job", icon: PlusIcon },
  { href: "/employer/listings", label: "My Listings", icon: ListIcon },
  { href: "/employer/applications", label: "Applications", icon: InboxIcon },
  { href: "/employer/pipeline", label: "Pipeline", icon: ColumnsIcon },
  { href: "/employer/settings", label: "Settings", icon: GearIcon },
];

export default function EmployerNav() {
  const pathname = usePathname();

  return (
    <nav className="employer-nav" aria-label="Employer">
      {ITEMS.map(({ href, label, icon: Icon, exact }) => {
        const active = exact ? pathname === href : pathname.startsWith(href);
        return (
          <Link key={href} href={href} className={active ? "active" : ""}>
            <Icon /> {label}
          </Link>
        );
      })}
    </nav>
  );
}
