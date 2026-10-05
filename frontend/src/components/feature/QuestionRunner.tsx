/* One question's interaction: selection, confidence, debounced draft save,
   submission with a stable request id, feedback, and the study shortcuts.
   Mounted with a `key` per item so its local state resets cleanly. */

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { FeedbackPanel } from "@/components/feature/FeedbackPanel";
import { QuestionCard } from "@/components/feature/QuestionCard";
import { Button } from "@/components/ui/Button";
import { SaveStatus, type SaveState } from "@/components/ui/SaveStatus";
import { isApiError, newRequestId } from "@/lib/api";
import { useShortcuts, type ShortcutBinding } from "@/lib/shortcuts";
import type { Confidence, SessionItemView, SessionView } from "@/lib/types";
import { useCardMutations } from "@/queries/review";
import { studyKeys, useSaveDraft, useSubmitAnswer } from "@/queries/study";
import { useUIStore } from "@/stores/ui";

interface QuestionRunnerProps {
  session: SessionView;
  item: SessionItemView;
  allAnswered: boolean;
  finishing: boolean;
  onNext: () => void;
  onFinish: () => void;
  onShowSummary: () => void;
  /** The server has a newer draft (another tab); the parent remounts this runner. */
  onStale: () => void;
}

export function QuestionRunner({
  session,
  item,
  allAnswered,
  finishing,
  onNext,
  onFinish,
  onShowSummary,
  onStale,
}: QuestionRunnerProps) {
  const queryClient = useQueryClient();
  const saveDraft = useSaveDraft();
  const submit = useSubmitAnswer();
  const cards = useCardMutations();
  const toggleFocusMode = useUIStore((s) => s.toggleFocusMode);

  const [selected, setSelected] = useState<string[]>(item.draft_selection ?? []);
  const [confidence, setConfidence] = useState<Confidence | null>(item.draft_confidence ?? null);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  // One request id per answer attempt: retries reuse it, so the server dedupes.
  const [requestId, setRequestId] = useState<string | null>(null);
  const [draftDirty, setDraftDirty] = useState(false);

  const id = session.id;
  const position = item.position;
  const pending = item.state === "pending";
  const sessionVersion = session.version;
  const saveDraftMutate = saveDraft.mutate;

  // Debounced draft save. The cleanup cancels a pending save whenever the draft
  // changes again, or when it is submitted (draftDirty flips back to false).
  useEffect(() => {
    if (!draftDirty || !pending) return undefined;
    const timer = window.setTimeout(() => {
      saveDraftMutate(
        {
          sessionId: id,
          position,
          selected_option_ids: selected,
          confidence,
          expected_version: sessionVersion,
        },
        {
          onSuccess: () => {
            setDraftDirty(false);
            setSaveState("saved");
          },
          onError: (error) => {
            if (isApiError(error, 409)) {
              setDraftDirty(false);
              setSaveState("stale");
              void queryClient.invalidateQueries({ queryKey: studyKeys.session(id) }).then(onStale);
            } else setSaveState("error");
          },
        },
      );
    }, 400);
    return () => window.clearTimeout(timer);
  }, [
    draftDirty,
    selected,
    confidence,
    position,
    pending,
    sessionVersion,
    id,
    saveDraftMutate,
    queryClient,
    onStale,
  ]);

  const markDirty = () => {
    setDraftDirty(true);
    setSaveState("saving");
  };
  const toggle = (optionId: string) => {
    if (!pending) return;
    let next: string[];
    if (item.select_count === 1) next = [optionId];
    else if (selected.includes(optionId)) next = selected.filter((o) => o !== optionId);
    else if (selected.length >= item.select_count) next = [...selected.slice(1), optionId];
    else next = [...selected, optionId];
    setSelected(next);
    markDirty();
  };
  const pickConfidence = (value: Confidence | null) => {
    setConfidence(value);
    markDirty();
  };

  const canSubmit = pending && selected.length === item.select_count && !submit.isPending;
  const doSubmit = () => {
    if (!canSubmit) return;
    setDraftDirty(false);
    const rid = requestId ?? newRequestId();
    setRequestId(rid);
    setSaveState("saving");
    submit.mutate(
      { sessionId: id, position, selected_option_ids: selected, confidence, request_id: rid },
      { onSuccess: () => setSaveState("saved"), onError: () => setSaveState("error") },
    );
  };

  const bindings = useMemo<ShortcutBinding[]>(() => {
    const keys: ShortcutBinding[] = [];
    for (let n = 1; n <= 6; n += 1) {
      keys.push({
        key: String(n),
        description: `Select option ${n}`,
        handler: () => {
          const option = item.options[n - 1];
          if (option) toggle(option.id);
        },
      });
    }
    keys.push({
      key: "Enter",
      description: "Submit or next",
      allowOnControls: false,
      handler: () => {
        if (pending) doSubmit();
        else if (allAnswered && session.status === "in_progress") onFinish();
        else onNext();
      },
    });
    keys.push({ key: "f", description: "Focus mode", handler: () => toggleFocusMode() });
    return keys;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- handlers close over fresh state each render
  }, [item, selected, confidence, canSubmit, allAnswered, pending, session.status]);
  useShortcuts(bindings);

  const answered = !pending;
  const isAssessment = session.kind === "assessment";
  return (
    <>
      <QuestionCard
        item={item}
        total={session.total}
        selected={selected}
        onToggle={toggle}
        confidence={confidence}
        onConfidence={pickConfidence}
        locked={answered || session.status !== "in_progress"}
      />
      <div className="study-actions">
        {!answered && session.status === "in_progress" ? (
          <Button
            variant="primary"
            size="lg"
            onClick={doSubmit}
            disabled={!canSubmit}
            busy={submit.isPending}
          >
            {isAssessment ? "Record answer" : "Check answer"}
          </Button>
        ) : null}
        {answered && !allAnswered ? (
          <Button variant="primary" onClick={onNext}>
            Next question
          </Button>
        ) : null}
        {allAnswered && session.status === "in_progress" ? (
          <Button variant="primary" size="lg" onClick={onFinish} busy={finishing}>
            {isAssessment ? "Submit assessment" : "Finish session"}
          </Button>
        ) : null}
        {session.status === "completed" ? (
          <Button variant="secondary" onClick={onShowSummary}>
            Summary
          </Button>
        ) : null}
        <SaveStatus state={saveState} onRetry={answered ? undefined : markDirty} />
      </div>
      {submit.isError ? (
        <p className="save-status save-status--error" role="alert">
          Answer not recorded: {submit.error.message}
        </p>
      ) : null}
      {answered && isAssessment && !session.feedback_visible ? (
        <p className="muted small">
          Recorded. Feedback appears after you submit the whole assessment.
        </p>
      ) : null}
      <FeedbackPanel
        item={item}
        cardBusy={cards.create.isPending}
        onMakeCard={() =>
          cards.create.mutate({
            source_kind: "mistake",
            item_key: item.item_key,
            front_md: item.stem_md,
            back_md: `**Decisive constraint:** ${item.feedback?.decisive_constraint ?? ""}\n\n${item.feedback?.explanation_md ?? ""}`,
          })
        }
      />
      {cards.create.isSuccess ? <p className="small dim">Card ready in Review.</p> : null}
    </>
  );
}
