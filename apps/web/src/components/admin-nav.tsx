import Link from "next/link";
import { Icon } from "./icons";

export function AdminNav({ active }: { active: "overview" | "violations" }) {
  return (
    <nav className="admin-nav" aria-label="Điều hướng quản trị">
      <Link href="/admin" data-active={active === "overview"}>
        <Icon name="dashboard" size={17} /> Tổng quan
      </Link>
      <Link href="/admin/violations" data-active={active === "violations"}>
        <Icon name="warning" size={17} /> Vi phạm
      </Link>
    </nav>
  );
}
