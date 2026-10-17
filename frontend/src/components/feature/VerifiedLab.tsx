import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { LabAttempts } from "@/components/feature/LabAttempts";
import { LabResult, LabSteps, type Busy } from "@/components/feature/LabSteps";
import { LabClusterChip, LabTask } from "@/components/feature/LabTask";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { graderCopy, phaseOf } from "@/lib/labs";
import type { LabView } from "@/lib/types";
import { useVerifierActions, verifierQueryOptions } from "@/queries/labs";

/** A lab graded by its backend (the lab cluster or the AWS emulator): live task, three steps,
    the verdict, the record. */
export function VerifiedLab({ lab, timeZone }: { lab: LabView; timeZone: string }) {
  const verifier = useQuery(verifierQueryOptions(lab.item_key));
  const { setup, check } = useVerifierActions(lab.item_key);
  const [openedTerminal, setOpenedTerminal] = useState(false);
  const copy = graderCopy(lab.verifier?.backend ?? "k16s");

  if (verifier.isPending) return <Spinner label={`Asking ${copy.name}`} />;
  if (verifier.isError) {
    return (
      <StateBlock
        tone="error"
        title="Could not read the lab's verifier"
        body={verifier.error.message}
        action={<Button onClick={() => void verifier.refetch()}>Try again</Button>}
      />
    );
  }
  const state = verifier.data;
  const phase = phaseOf(state, openedTerminal);
  const busy: Busy = setup.isPending ? "setup" : check.isPending ? "check" : null;
  const blocked =
    !state.configured || !state.reachable || !state.task || state.unavailable_reason !== null;
  const actionError = setup.error ?? check.error;
  const latest = state.attempts[0];
  const unavailable = setup.data?.unavailable_reason ?? check.data?.unavailable_reason ?? null;

  return (
    <div className="verified-lab stack">
      <LabClusterChip state={state} />
      {!state.configured ? (
        <StateBlock
          title={`This lab needs ${copy.needs}`}
          body={
            state.spec.backend === "k16s" ? (
              <>
                Verified labs run on your own K16S instance. Set <code>K16S_BASE_URL</code> (and{" "}
                <code>K16S_PUBLIC_URL</code> for the terminal) and reload; see docs/labs-k16s.md.
                Nothing is installed from here.
              </>
            ) : (
              <>
                AWS labs are graded against your own LocalEmu emulator. Set{" "}
                <code>LOCALEMU_BASE_URL</code> to it and reload. Nothing is installed from here, and
                nothing touches a real AWS account.
              </>
            )
          }
        />
      ) : null}
      {state.configured && !state.reachable ? (
        <StateBlock
          tone="error"
          title={`${copy.subject} did not answer`}
          body={state.message}
          action={<Button onClick={() => void verifier.refetch()}>Try again</Button>}
        />
      ) : null}
      <LabTask state={state} />
      {latest && (phase === "passed" || phase === "failed") ? <LabResult attempt={latest} /> : null}
      <LabSteps
        state={state}
        phase={phase}
        busy={busy}
        disabled={blocked}
        onSetup={() => {
          setOpenedTerminal(false);
          setup.mutate();
        }}
        onCheck={() => check.mutate()}
        onOpenTerminal={() => setOpenedTerminal(true)}
      />
      {busy ? (
        <p className="muted small" role="status">
          {busy === "setup" ? copy.setupBusy : copy.checkBusy}
        </p>
      ) : null}
      {unavailable && !busy ? (
        <p className="save-status save-status--stale" role="status">
          {unavailable}
        </p>
      ) : null}
      {actionError ? (
        <p className="save-status save-status--error" role="alert">
          {actionError.message}
        </p>
      ) : null}
      <section className="card card--quiet" aria-labelledby="attempts-title">
        <h3 id="attempts-title" className="card__title">
          Attempts
        </h3>
        <LabAttempts attempts={state.attempts} timeZone={timeZone} />
      </section>
    </div>
  );
}
