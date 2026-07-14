import type { Metadata } from "next";
import EmployerRegisterForm from "@/components/EmployerRegisterForm";

export const metadata: Metadata = { title: "Employer sign-up" };

export default function EmployerRegisterPage() {
  return (
    <div className="auth-wrap">
      <EmployerRegisterForm />
    </div>
  );
}
