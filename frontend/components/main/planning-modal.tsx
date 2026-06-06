"use client";

/**
 * B4-S2 후속: 토픽(카테고리) 카드 클릭 시 뜨는 angle/SEG 선택 모달.
 *
 * UX:
 * - 두 셀렉터 모두 디폴트는 "자동(회전)" → 1-클릭 패스로도 기존 동작과 동일
 * - 사용자가 명시 선택한 항목만 override 로 백엔드에 전달
 * - presets 는 useQuery 로 1회 fetch + 무한 cache (브라우저 세션 동안 변하지 않음)
 *
 * 회귀 안전장치:
 * - selection_override 미지정 (둘 다 auto) 시 백엔드 selector 가 기존 round_robin 그대로 동작
 * - 모달 자체가 dismiss 가능 — 사용자가 esc/취소 누르면 generate 호출 자체가 발생 X
 */
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  fetchPlanningPresets,
  type PlanningAnglePreset,
  type PlanningSegmentPreset,
  type SelectionOverride,
} from "@/lib/api";
import { CATEGORY_LABEL_MAP, type CategoryId } from "@/lib/constants";

interface Props {
  open: boolean;
  category: CategoryId | null;
  onClose: () => void;
  onConfirm: (override: SelectionOverride) => void;
  pending: boolean;
}

const AUTO_KEY = "__auto__";

export function PlanningModal({
  open,
  category,
  onClose,
  onConfirm,
  pending,
}: Props) {
  const [angleKey, setAngleKey] = useState<string>(AUTO_KEY);
  const [segmentKey, setSegmentKey] = useState<string>(AUTO_KEY);

  const presetsQuery = useQuery({
    queryKey: ["planning-presets"],
    queryFn: fetchPlanningPresets,
    enabled: open,
    staleTime: Infinity,
  });

  // 모달 열릴 때마다 디폴트 "자동" 으로 리셋 — 직전 선택이 다음 run 에 끌려가지 않게.
  useEffect(() => {
    if (open) {
      setAngleKey(AUTO_KEY);
      setSegmentKey(AUTO_KEY);
    }
  }, [open]);

  // Esc 키로 닫기
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !pending) onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose, pending]);

  const handleConfirm = () => {
    const override: SelectionOverride = {
      angle: angleKey === AUTO_KEY ? null : angleKey,
      audience_segment: segmentKey === AUTO_KEY ? null : segmentKey,
    };
    onConfirm(override);
  };

  const categoryLabel = category ? CATEGORY_LABEL_MAP[category] : "";

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center px-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* Backdrop */}
          <motion.button
            type="button"
            aria-label="모달 닫기"
            onClick={() => {
              if (!pending) onClose();
            }}
            className="absolute inset-0 bg-black/60"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />

          {/* Modal card */}
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="angle 과 SEG 선택"
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.96 }}
            transition={{ type: "spring", stiffness: 360, damping: 30 }}
            className="relative z-10 w-full max-w-2xl overflow-hidden rounded-2xl border border-border-subtle bg-bg-elevated shadow-2xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-border-subtle px-6 py-4">
              <div>
                <h2 className="font-korean text-base font-semibold text-text-primary sm:text-lg">
                  {categoryLabel
                    ? `${categoryLabel} — 어떤 각도로?`
                    : "각도와 독자군 선택"}
                </h2>
                <p className="mt-1 font-korean text-xs text-text-muted sm:text-sm">
                  둘 다 <span className="text-text-secondary">자동</span> 으로 두면
                  시스템이 회전 순서대로 배정합니다.
                </p>
              </div>
              <button
                type="button"
                onClick={onClose}
                disabled={pending}
                className="rounded p-1 text-text-muted transition hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-50"
                aria-label="닫기"
              >
                <X className="h-5 w-5" />
              </button>
            </header>

            <div className="max-h-[60vh] space-y-6 overflow-y-auto px-6 py-5">
              {presetsQuery.isLoading && (
                <p className="font-korean text-sm text-text-muted">
                  선택지 로드중...
                </p>
              )}
              {presetsQuery.isError && (
                <p className="font-korean text-sm text-state-danger">
                  선택지 로드 실패: {(presetsQuery.error as Error).message}
                </p>
              )}

              {presetsQuery.data && (
                <>
                  <AngleSection
                    angles={presetsQuery.data.angles}
                    selected={angleKey}
                    onSelect={setAngleKey}
                  />
                  <SegmentSection
                    segments={presetsQuery.data.segments}
                    selected={segmentKey}
                    onSelect={setSegmentKey}
                  />
                </>
              )}
            </div>

            <footer className="flex items-center justify-end gap-2 border-t border-border-subtle px-6 py-4">
              <button
                type="button"
                onClick={onClose}
                disabled={pending}
                className="rounded-md border border-border-subtle px-4 py-2 font-korean text-sm text-text-secondary transition hover:border-border-strong hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-50"
              >
                취소
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                disabled={pending || !presetsQuery.data}
                className="rounded-md bg-accent-pink px-5 py-2 font-korean text-sm font-semibold text-white transition hover:bg-accent-pink-hover disabled:cursor-wait disabled:opacity-60"
              >
                {pending ? "시작 중…" : "이대로 생성"}
              </button>
            </footer>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function AngleSection({
  angles,
  selected,
  onSelect,
}: {
  angles: PlanningAnglePreset[];
  selected: string;
  onSelect: (key: string) => void;
}) {
  return (
    <section>
      <h3 className="mb-2 font-korean text-sm font-semibold text-text-primary">
        Angle (콘텐츠 각도)
      </h3>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <ChipOption
          label="자동 (회전)"
          subtitle="시스템이 round-robin 배정"
          active={selected === AUTO_KEY}
          onClick={() => onSelect(AUTO_KEY)}
        />
        {angles.map((a) => (
          <ChipOption
            key={a.key}
            label={a.label}
            subtitle={a.directive}
            active={selected === a.key}
            disabled={!a.enabled}
            onClick={() => a.enabled && onSelect(a.key)}
          />
        ))}
      </div>
    </section>
  );
}

function SegmentSection({
  segments,
  selected,
  onSelect,
}: {
  segments: PlanningSegmentPreset[];
  selected: string;
  onSelect: (key: string) => void;
}) {
  return (
    <section>
      <h3 className="mb-2 font-korean text-sm font-semibold text-text-primary">
        SEG (독자군)
      </h3>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <ChipOption
          label="자동 (회전)"
          subtitle="시스템이 rotate 배정"
          active={selected === AUTO_KEY}
          onClick={() => onSelect(AUTO_KEY)}
        />
        {segments.map((s) => (
          <ChipOption
            key={s.key}
            label={s.label}
            subtitle={s.persona}
            active={selected === s.key}
            onClick={() => onSelect(s.key)}
          />
        ))}
      </div>
    </section>
  );
}

function ChipOption({
  label,
  subtitle,
  active,
  disabled,
  onClick,
}: {
  label: string;
  subtitle: string;
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      className={cn(
        "rounded-lg border px-3 py-2 text-left transition",
        active
          ? "border-accent-pink bg-accent-pink-soft"
          : "border-border-subtle bg-bg-secondary hover:border-border-strong",
        disabled && "cursor-not-allowed opacity-40 hover:border-border-subtle",
      )}
    >
      <div
        className={cn(
          "font-korean text-sm font-semibold",
          active ? "text-text-primary" : "text-text-primary",
        )}
      >
        {label}
        {disabled && (
          <span className="ml-1 text-[10px] text-text-muted">(비활성)</span>
        )}
      </div>
      <div className="mt-0.5 font-korean text-xs text-text-muted line-clamp-2">
        {subtitle}
      </div>
    </button>
  );
}
