import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, Keyboard } from 'lucide-react';
import type { Route } from '../app/router';
import { buildHash, lastViewHref, navigate, patchParams } from '../app/router';
import { loadMeta, useAsync } from '../data/api';
import type { Meta, Policy, Stream } from '../data/types';
import { POLICY_HEX, POLICY_LABEL, streamTitle } from '../data/labels';
import { Async, ErrorState, Spinner } from '../components/ui';
import { SPEEDS } from '../replay/controller';
import { resolvePolicy, useController, useReplaySnapshot, useStream, useStreamIndex } from '../replay/useReplay';
import { ShelfCanvas } from '../replay/ShelfCanvas';
import { NearBins } from '../replay/NearBins';
import { ForkTimeline } from '../replay/ForkTimeline';
import { CurvePanel } from '../replay/CurvePanel';
import { StepReadout } from '../replay/StepReadout';
import { DecisionPanel } from '../replay/DecisionPanel';
import { HindsightTab } from './replay/HindsightTab';
import { EvidenceTab } from './replay/EvidenceTab';
import { PolicyPicker } from './replay/PolicyPicker';
import type { SideState, StepView } from '../replay/controller';
import s from './ReplayView.module.css';

type TabKey = 'step' | 'decision' | 'hindsight' | 'evidence';
const DEFAULT_INSTANCE = 'confirmation_weibull_3_45_r0__descending';

export function ReplayView({ route }: { route: Route }) {
  const meta = useAsync('meta', () => loadMeta());
  const index = useStreamIndex();

  if (!route.id) {
    return <PickPrompt />;
  }

  return (
    <div className={s.page}>
      <Async state={meta}>
        {(m) => (
          <Async state={index}>{(idx) => <ReplayBody route={route} meta={m} index={idx} />}</Async>
        )}
      </Async>
    </div>
  );
}

function PickPrompt() {
  // No instance in the URL: send to a representative confirmation stream.
  useEffect(() => {
    navigate(buildHash('replay', DEFAULT_INSTANCE, { a: 'SELECTOR', b: 'SBS', t: 500, view: 'observed' }), {
      replace: true,
    });
  }, []);
  return <Spinner label="正在打开一个示例样本…" />;
}

function ReplayBody({ route, meta, index }: { route: Route; meta: Meta; index: Map<string, Stream> }) {
  const instance = route.id!;
  const stream = useStream(index, instance);
  const sbs = meta.summary.training.sbs as Policy;
  const featureNames = meta.protocol.features.names;

  const available = useMemo(() => (stream ? stream.runs.map((r) => r.policy) : []), [stream]);
  const aToken = route.params.get('a') ?? (available.includes('SELECTOR') ? 'SELECTOR' : 'BF');
  const bToken = route.params.get('b');
  const requestedA = resolvePolicy(aToken, sbs) ?? 'SELECTOR';
  const requestedB = bToken ? resolvePolicy(bToken, sbs) : null;
  // A training stream has no SELECTOR / published_EoH runs. Never try to load a
  // run that does not exist — fall back to a real one and fix the URL.
  const policyA = available.length === 0 || available.includes(requestedA)
    ? requestedA
    : available.includes('SELECTOR')
      ? 'SELECTOR'
      : (sbs as Policy);
  const policyB = requestedB && (available.length === 0 || available.includes(requestedB)) ? requestedB : null;
  const retrospective = route.params.get('view') === 'retro';

  useEffect(() => {
    if (!stream) return;
    if (policyA !== requestedA || policyB !== requestedB) {
      patchParams({ a: policyA, b: policyB ?? null }, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stream, policyA, policyB, requestedA, requestedB]);

  const controller = useController();
  const snap = useReplaySnapshot(controller);

  // Target t for the NEXT (re)load, read via ref so t-only changes do not
  // reload. A policy switch carries t explicitly in the URL; a fresh stream
  // with no t defaults to the decision boundary rather than inheriting the
  // previous run's position.
  const tParamRef = useRef(clampInt(route.params.get('t'), 500));
  tParamRef.current = clampInt(route.params.get('t'), 500);
  const loadKey = `${instance}|${policyA}|${policyB ?? ''}`;
  useEffect(() => {
    if (!stream) return;
    // load() dedupes when the same key is already ready/loading, and reloads
    // after a dispose (which resets the controller to idle).
    void controller.load(stream, policyA, policyB, tParamRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stream, loadKey, controller]);

  // A same-stream hash/history change may only change t; no run reload is
  // needed, but the visible position must still follow that explicit URL.
  const requestedPosition = clampInt(route.params.get('t'), 500);
  useEffect(() => {
    const current = controller.getSnapshot();
    if (current.status === 'ready' && current.key === loadKey && current.t !== requestedPosition) {
      controller.pause();
      controller.seek(requestedPosition);
    }
  }, [controller, loadKey, requestedPosition]);

  // Reflect t to the URL when paused (so refresh restores position) without
  // spamming during playback.
  useEffect(() => {
    if (snap.status === 'ready' && !snap.playing) {
      patchParams({ t: snap.t }, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snap.t, snap.playing, snap.status]);

  // Keyboard shortcuts (space/arrows/home/end) when not typing in a field.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      // Let interactive controls handle their own keys. In particular the
      // timeline slider steps on ArrowLeft/Right itself; without this the
      // global handler would step a second time and skip the 500 boundary.
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.tagName === 'BUTTON' ||
        target.isContentEditable ||
        target.closest('[role="slider"]')
      ) {
        return;
      }
      if (e.key === ' ') {
        e.preventDefault();
        controller.toggle();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        controller.step(e.shiftKey ? 10 : 1);
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        controller.step(e.shiftKey ? -10 : -1);
      } else if (e.key === 'Home') {
        controller.seek(0);
      } else if (e.key === 'End') {
        controller.seek(snap.total);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [controller, snap.total]);

  if (!stream) {
    return (
      <ErrorState
        error={new Error(`找不到输入流 ${instance}。可能是地址有误。`)}
        onRetry={() => navigate(lastViewHref('samples'))}
      />
    );
  }

  return (
    <ReplayReady
      key={instance}
      controller={controller}
      snap={snap}
      stream={stream}
      meta={meta}
      policyA={policyA}
      policyB={policyB}
      available={available}
      sbs={sbs}
      retrospective={retrospective}
      featureNames={featureNames}
      requestedT={tParamRef.current}
    />
  );
}

function ReplayReady({
  controller,
  snap,
  stream,
  meta,
  policyA,
  policyB,
  available,
  sbs,
  retrospective,
  featureNames,
  requestedT,
}: {
  controller: ReturnType<typeof useController>;
  snap: ReturnType<typeof useReplaySnapshot>;
  stream: Stream;
  meta: Meta;
  policyA: Policy;
  policyB: Policy | null;
  available: Policy[];
  sbs: Policy;
  retrospective: boolean;
  featureNames: string[];
  requestedT: number;
}) {
  const [tab, setTab] = useState<TabKey>('step');
  const comparing = policyB !== null;
  const ready = snap.status === 'ready';

  // Auto-reveal the decision tab the first time playback stops at the boundary.
  useEffect(() => {
    if (snap.pausedAtBoundary) setTab('decision');
  }, [snap.pausedAtBoundary]);

  const setPolicies = useCallback(
    (a: string, b: string | null) => {
      patchParams({ a, b: b ?? null, t: snap.t }, { replace: false });
    },
    [snap.t],
  );

  const setView = useCallback(
    (retro: boolean) => patchParams({ view: retro ? 'retro' : null }, { replace: false }),
    [],
  );

  const runASel = useMemo(() => {
    const d = controller.run('a');
    return d && d.decision ? d : controller.run('b')?.decision ? controller.run('b') : null;
  }, [controller, snap.version]);

  const decisionData = ready ? (controller.decision(runASel === controller.run('b') ? 'b' : 'a', retrospective) as Record<string, unknown> | null) : null;
  const decisionAvailable = Boolean(decisionData && decisionData.available);

  return (
    <>
      <header className={s.head}>
        <div className={s.headTop}>
          <a className={s.back} href={lastViewHref('samples')}>
            <ArrowLeft size={15} aria-hidden /> 样本
          </a>
          <div className={s.titleWrap}>
            <h1 className={s.title}>{streamTitle(stream)}</h1>
            <span className={`${s.instanceId} mono`}>{stream.instance_id}</span>
          </div>
        </div>
        <div className={s.headControls}>
          <PolicyPicker policyA={policyA} policyB={policyB} available={available} sbs={sbs} onChange={setPolicies} />
          <ViewToggle retrospective={retrospective} onChange={setView} />
        </div>
      </header>

      {snap.status === 'error' && snap.error ? (
        <ErrorState error={snap.error} onRetry={() => controller.load(stream, policyA, policyB, requestedT)} />
      ) : !ready ? (
        <Spinner label="正在校验并载入轨迹…" />
      ) : (
        <div className={s.layout}>
          <div className={s.stage}>
            <ShelfCanvas
              run={controller.run('a')!}
              t={snap.t}
              colorHex={POLICY_HEX[policyA]}
              label={POLICY_LABEL[policyA]}
              boundary={snap.boundary}
            />
            {comparing && controller.run('b') && (
              <ShelfCanvas
                run={controller.run('b')!}
                t={snap.t}
                colorHex={POLICY_HEX[policyB!]}
                label={POLICY_LABEL[policyB!]}
                boundary={snap.boundary}
              />
            )}

            <div className={s.nearWrap}>
              <h2 className={s.stageH2}>当前箱附近（{POLICY_LABEL[policyA]}）</h2>
              <NearBins
                binOf={(bin) => controller.bin('a', bin) as never}
                activeBin={activeBinOf(controller.state('a'))}
                currentIndex={snap.t - 1}
                currentSize={snap.t > 0 ? currentSizeOf(controller.items(snap.t - 1, 1)) : null}
                capacity={stream.capacity}
                slotCount={controller.run('a')!.remaining.length}
                colorHex={POLICY_HEX[policyA]}
              />
            </div>

            <div className={s.curveWrap}>
              <CurvePanel
                curveA={controller.curve('a')!}
                curveB={comparing ? controller.curve('b') : null}
                labelA={POLICY_LABEL[policyA]}
                labelB={comparing ? POLICY_LABEL[policyB!] : null}
                colorA={POLICY_HEX[policyA]}
                colorB={comparing ? POLICY_HEX[policyB!] : '#7a7f87'}
                t={snap.t}
                total={snap.total}
                boundary={snap.boundary}
                retrospective={retrospective}
                sharedPrefix={policyA !== 'published_EoH' && policyB !== 'published_EoH'}
              />
            </div>
          </div>

          <aside className={s.explain}>
            <div className={s.tabs} role="tablist" aria-label="解释面板">
              <Tab id="step" active={tab} onClick={setTab}>
                当前一步
              </Tab>
              <Tab id="decision" active={tab} onClick={setTab}>
                第 500 项决策
              </Tab>
              <Tab id="hindsight" active={tab} onClick={setTab}>
                事后对照
              </Tab>
              <Tab id="evidence" active={tab} onClick={setTab}>
                证据
              </Tab>
            </div>

            <div className={s.tabBody} role="tabpanel">
              {tab === 'step' && (
                <StepReadout
                  state={controller.state('a')}
                  step={snap.t > 0 ? (controller.items(snap.t - 1, 1)[0] ?? null) : null}
                  capacity={stream.capacity}
                  slotCount={controller.run('a')!.remaining.length}
                />
              )}
              {tab === 'decision' &&
                (decisionAvailable && decisionData ? (
                  <DecisionPanel
                    decision={decisionData as never}
                    run={runASel}
                    model={meta.model}
                    featureNames={featureNames}
                  />
                ) : (
                  <DecisionGate retrospective={retrospective} boundary={snap.boundary} onReveal={() => { controller.seek(snap.boundary); }} onRetro={() => setView(true)} hasSelector={Boolean(runASel)} />
                ))}
              {tab === 'hindsight' && <HindsightTab stream={stream} meta={meta} />}
              {tab === 'evidence' && <EvidenceTab controller={controller} stream={stream} comparing={comparing} />}
            </div>
          </aside>

          <div className={s.timelineBar}>
            <ForkTimeline
              t={snap.t}
              total={snap.total}
              boundary={snap.boundary}
              playing={snap.playing}
              speed={snap.speed}
              speeds={SPEEDS}
              onSeek={(x) => controller.seek(x)}
              onStep={(d) => controller.step(d)}
              onTogglePlay={() => controller.toggle()}
              onReset={() => controller.reset()}
              onSpeed={(sp) => controller.setSpeed(sp)}
            />
            <p className={s.kbd}>
              <Keyboard size={13} aria-hidden /> 空格播放/暂停 · ←/→ 单步（Shift ±10）· PgUp/PgDn ±100 · Home/End 端点
            </p>
          </div>
        </div>
      )}
    </>
  );
}

function Tab({ id, active, onClick, children }: { id: TabKey; active: TabKey; onClick: (t: TabKey) => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active === id}
      className={s.tab}
      data-active={active === id || undefined}
      onClick={() => onClick(id)}
    >
      {children}
    </button>
  );
}

function ViewToggle({ retrospective, onChange }: { retrospective: boolean; onChange: (retro: boolean) => void }) {
  return (
    <div className={s.viewToggle} role="group" aria-label="信息视角">
      <button type="button" data-active={!retrospective || undefined} onClick={() => onChange(false)}>
        当时已知
      </button>
      <button type="button" data-active={retrospective || undefined} onClick={() => onChange(true)}>
        事后对照
      </button>
    </div>
  );
}

function DecisionGate({
  retrospective,
  boundary,
  onReveal,
  onRetro,
  hasSelector,
}: {
  retrospective: boolean;
  boundary: number;
  onReveal: () => void;
  onRetro: () => void;
  hasSelector: boolean;
}) {
  if (!hasSelector) {
    return (
      <p className={s.gate}>
        当前对照里没有选择器运行。把 A 或 B 设为“前缀选择器”即可查看第 {boundary} 项的决策。
      </p>
    );
  }
  return (
    <div className={s.gate}>
      <p>
        {retrospective
          ? '决策尚未可见。'
          : `按“当时已知”视角，决策在处理满 ${boundary} 项时揭晓——此刻选择器才读取前缀。`}
      </p>
      <div className={s.gateBtns}>
        <button type="button" className={s.gatePrimary} onClick={onReveal}>
          跳到第 {boundary} 项
        </button>
        {!retrospective && (
          <button type="button" className={s.gateGhost} onClick={onRetro}>
            切到事后对照直接查看
          </button>
        )}
      </div>
    </div>
  );
}

function clampInt(value: string | null, fallback: number): number {
  const n = value === null ? NaN : Number(value);
  return Number.isFinite(n) ? Math.max(0, Math.round(n)) : fallback;
}

function activeBinOf(state: SideState | null): number | null {
  return state && state.processed > 0 ? state.activeBin : null;
}

function currentSizeOf(items: StepView[]): number | null {
  return items[0]?.size ?? null;
}
