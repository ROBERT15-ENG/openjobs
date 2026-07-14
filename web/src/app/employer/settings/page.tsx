import type { Metadata } from "next";
import SettingsForms from "@/components/employer/SettingsForms";
import { getSessionUser } from "@/lib/session";

export const metadata: Metadata = { title: "Settings" };

export default async function SettingsPage() {
  const user = (await getSessionUser())!;

  return (
    <>
      <h1 className="page-title">Company Settings</h1>
      <p className="page-sub">Update your company profile and preferences.</p>
      <SettingsForms user={user} />
    </>
  );
}
