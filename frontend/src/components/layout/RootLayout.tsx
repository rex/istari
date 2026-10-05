import { Outlet } from "@tanstack/react-router";
import { Suspense } from "react";

import { Spinner } from "@/components/ui/Spinner";

export function RootLayout() {
  return (
    <Suspense fallback={<Spinner label="Loading Istari" />}>
      <Outlet />
    </Suspense>
  );
}
