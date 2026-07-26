"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

function apiBase() {
  if (typeof window === "undefined") return "http://127.0.0.1:8000/api/v1";
  // Use the same host through which the UI was opened. A hard-coded 127.0.0.1
  // breaks when the interface is opened as localhost or through another host.
  return `${window.location.protocol}//${window.location.hostname}:8000/api/v1`;
}

type Section = "overview" | "convert" | "models" | "accounting" | "imports";
type Model = {
  provider_code: string; code: string; display_name: string; context_window: number;
  max_output_tokens?: number; status: string; capabilities: string[];
  rpm?: number; tpm?: number; rpd?: number;
};
type Provider = { code: string; display_name: string; adapter: string; secret_ref?: string; enabled: boolean };
type Price = { model_id: string; currency: string; input_per_million?: string; output_per_million?: string };
type Budget = { scope: string; amount: string; currency: string; period: string; warning_ratio: string };
type Dashboard = {
  models: number; providers: number; requests: number; input_tokens: number; output_tokens: number;
  total_cost: string; currency: string; successful: number; failed: number;
  by_model: Record<string, { requests: number; input_tokens: number; output_tokens: number; cost: string }>;
  repository: string;
};

const navigation: { id: Section; label: string; hint: string }[] = [
  { id: "overview", label: "Обзор", hint: "Состояние системы" },
  { id: "convert", label: "Конвертация", hint: "Документы и диаграммы" },
  { id: "models", label: "Каталог", hint: "Провайдеры и модели" },
  { id: "accounting", label: "Учёт", hint: "Тарифы, бюджеты, usage" },
  { id: "imports", label: "Импорт", hint: "Настройки и история" },
];

function modelId(model: Model) { return `${model.provider_code}:${model.code}`; }
function compact(value: number) {
  return new Intl.NumberFormat("ru-RU", { notation: value > 9999 ? "compact" : "standard", maximumFractionDigits: 1 }).format(value);
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const endpoint = `${apiBase()}${path}`;
  let response: Response;
  try {
    response = await fetch(endpoint, init);
  } catch (error) {
    throw new Error(
      `REST API недоступен (${endpoint}). Запустите интерфейс командой «python convert2md.py web».`
    );
  }
  if (!response.ok) {
    let message = `Ошибка ${response.status}`;
    try { message = (await response.json()).detail || message; } catch {}
    throw new Error(message);
  }
  return response.json();
}

export default function Home() {
  const [section, setSection] = useState<Section>("overview");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [models, setModels] = useState<Model[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [prices, setPrices] = useState<Price[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [dash, modelRows, providerRows, priceRows, budgetRows] = await Promise.all([
        api<Dashboard>("/dashboard"), api<Model[]>("/models"), api<Provider[]>("/providers"),
        api<Price[]>("/prices"), api<Budget[]>("/budgets"),
      ]);
      setDashboard(dash); setModels(modelRows); setProviders(providerRows);
      setPrices(priceRows); setBudgets(budgetRows); setConnected(true);
    } catch {
      setConnected(false);
    }
  }, []);

  useEffect(() => { refresh(); const timer = setInterval(refresh, 15000); return () => clearInterval(timer); }, [refresh]);
  const flash = (text: string, kind: "ok" | "error" = "ok") => {
    setNotice({ text, kind }); window.setTimeout(() => setNotice(null), 4500);
  };
  const submit = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true);
    try { await action(); flash(success); await refresh(); }
    catch (error) { flash(error instanceof Error ? error.message : "Операция не выполнена", "error"); }
    finally { setBusy(false); }
  };

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">M↓</div>
          <div><strong>Convert2MD</strong><span>Control room</span></div>
        </div>
        <nav aria-label="Разделы приложения">
          {navigation.map(item => (
            <button key={item.id} className={section === item.id ? "nav-item active" : "nav-item"}
              onClick={() => setSection(item.id)}>
              <span className="nav-symbol">{item.id === "overview" ? "◫" : item.id === "convert" ? "↯" : item.id === "models" ? "◇" : item.id === "accounting" ? "⌁" : "⇣"}</span>
              <span><b>{item.label}</b><small>{item.hint}</small></span>
            </button>
          ))}
        </nav>
        <div className="connection-card">
          <span className={connected ? "status-dot online" : "status-dot"} />
          <div><b>{connected ? "Система готова" : "API недоступен"}</b>
            <small>{connected ? "Данные синхронизированы" : "Запустите web_server.py"}</small></div>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Локальная рабочая область</p>
            <h1>{navigation.find(item => item.id === section)?.label}</h1>
          </div>
          <div className="top-actions">
            <button className="ghost" onClick={refresh}>Обновить</button>
            <button className="primary compact" onClick={() => setSection("convert")}>+ Конвертировать</button>
          </div>
        </header>

        {section === "overview" && <Overview dashboard={dashboard} models={models} setSection={setSection} />}
        {section === "convert" && <ConvertPanel models={models} submit={submit} busy={busy} />}
        {section === "models" && <Catalog models={models} providers={providers} submit={submit} busy={busy} />}
        {section === "accounting" && <Accounting dashboard={dashboard} models={models} prices={prices} budgets={budgets} submit={submit} busy={busy} />}
        {section === "imports" && <Imports submit={submit} busy={busy} />}
      </section>
      {notice && <div role="status" className={`toast ${notice.kind}`}>{notice.kind === "ok" ? "✓" : "!"} {notice.text}</div>}
    </main>
  );
}

function Overview({ dashboard, models, setSection }: { dashboard: Dashboard | null; models: Model[]; setSection: (s: Section) => void }) {
  const topModels = Object.entries(dashboard?.by_model || {}).sort((a, b) => b[1].requests - a[1].requests).slice(0, 4);
  const maxRequests = Math.max(1, ...topModels.map(([, value]) => value.requests));
  return <div className="content">
    <section className="hero-panel">
      <div><p className="eyebrow light">Единый центр управления</p>
        <h2>Документы входят.<br/><em>Чистый Markdown выходит.</em></h2>
        <p>Конвертация, модели, лимиты и расходы — в одном локальном интерфейсе.</p>
        <button className="primary light-button" onClick={() => setSection("convert")}>Начать конвертацию <span>→</span></button>
      </div>
      <div className="hero-meter">
        <div className="orbit"><span>{dashboard?.models ?? "—"}</span><small>моделей<br/>в каталоге</small></div>
      </div>
    </section>
    <section className="metrics">
      <Metric label="Запросов" value={compact(dashboard?.requests || 0)} note={`${dashboard?.successful || 0} успешно`} />
      <Metric label="Входные токены" value={compact(dashboard?.input_tokens || 0)} note="за всё время" />
      <Metric label="Стоимость" value={`${dashboard?.total_cost || "0"} ${dashboard?.currency || "USD"}`} note="по снимкам тарифов" />
      <Metric label="Провайдеры" value={String(dashboard?.providers || 0)} note="подключено локально" />
    </section>
    <div className="grid-two">
      <section className="card">
        <div className="card-head"><div><p className="eyebrow">Активность</p><h3>Использование по моделям</h3></div><button className="text-button" onClick={() => setSection("accounting")}>Подробнее</button></div>
        <div className="bars">
          {topModels.length ? topModels.map(([id, value]) => <div className="bar-row" key={id}>
            <div><b>{id.split(":").pop()}</b><span>{value.requests} запросов</span></div>
            <div className="bar-track"><i style={{ width: `${Math.max(8, value.requests / maxRequests * 100)}%` }} /></div>
          </div>) : <Empty text="Использование появится после первого запроса" />}
        </div>
      </section>
      <section className="card">
        <div className="card-head"><div><p className="eyebrow">Каталог</p><h3>Готовые модели</h3></div><button className="text-button" onClick={() => setSection("models")}>Открыть</button></div>
        <div className="model-stack">
          {models.slice(0, 4).map(model => <div className="model-mini" key={modelId(model)}>
            <span className="provider-badge">{model.provider_code.slice(0, 1).toUpperCase()}</span>
            <div><b>{model.display_name}</b><small>{compact(model.context_window)} контекст · {model.capabilities.join(", ")}</small></div>
            <i className={model.status === "active" ? "live" : ""} />
          </div>)}
        </div>
      </section>
    </div>
    <p className="repo-line">Хранилище: <code>{dashboard?.repository || "подключение..."}</code></p>
  </div>;
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return <article className="metric"><p>{label}</p><strong>{value}</strong><span>{note}</span></article>;
}

function ConvertPanel({ models, submit, busy }: { models: Model[]; submit: Function; busy: boolean }) {
  const [mode, setMode] = useState<"document" | "diagram">("document");
  const [files, setFiles] = useState<File[]>([]);
  const [model, setModel] = useState("google:gemini-3.1-flash-lite");
  const [noFilter, setNoFilter] = useState(false);
  const [results, setResults] = useState<{ filename: string; markdown: string; archive_filename?: string; archive_base64?: string }[]>([]);
  const visionModels = useMemo(
    () => models.filter(item =>
      item.provider_code === "google"
      && item.capabilities.includes("vision")
      && ["active", "experimental"].includes(item.status)
    ),
    [models],
  );
  useEffect(() => {
    if (visionModels.length && !visionModels.some(item => modelId(item) === model)) {
      setModel(modelId(visionModels[0]));
    }
  }, [visionModels, model]);
  const accept = mode === "document" ? ".pdf,.doc,.docx" : ".png,.jpg,.jpeg";
  const run = () => submit(async () => {
    const converted = [];
    for (const file of files) {
      const body = new FormData(); body.append("file", file);
      const query = mode === "document" ? `?no_filter=${noFilter}` : `?model_id=${encodeURIComponent(model)}`;
      converted.push(await api<{ filename: string; markdown: string; archive_filename?: string; archive_base64?: string }>(`/convert/${mode}${query}`, { method: "POST", body }));
    }
    setResults(converted);
  }, `${files.length} файл(а) обработано`);
  const download = (result: { filename: string; markdown: string; archive_filename?: string; archive_base64?: string }) => {
    let blob: Blob; let filename = result.filename;
    if (result.archive_base64) {
      const bytes = Uint8Array.from(atob(result.archive_base64), char => char.charCodeAt(0));
      blob = new Blob([bytes], { type: "application/zip" }); filename = result.archive_filename || `${result.filename}.zip`;
    } else {
      blob = new Blob([result.markdown], { type: "text/markdown" });
    }
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a"); link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url);
  };
  return <div className="content narrow">
    <div className="segmented">
      <button className={mode === "document" ? "selected" : ""} onClick={() => { setMode("document"); setFiles([]); }}>Документы</button>
      <button className={mode === "diagram" ? "selected" : ""} onClick={() => { setMode("diagram"); setFiles([]); }}>Диаграммы → Mermaid</button>
    </div>
    <section className="card converter-card">
      <div className="card-head"><div><p className="eyebrow">Новая задача</p><h2>{mode === "document" ? "Конвертировать в Markdown" : "Распознать диаграммы"}</h2></div><span className="step-pill">01 / загрузка</span></div>
      <label className="dropzone">
        <input type="file" multiple accept={accept} onChange={event => setFiles(Array.from(event.target.files || []))} />
        <span className="drop-icon">⇧</span><b>Перетащите файлы или выберите на диске</b>
        <small>{mode === "document" ? "PDF, DOCX или DOC" : "PNG, JPG или JPEG"} · можно несколько</small>
      </label>
      {files.length > 0 && <div className="file-list">{files.map(file => <div key={file.name}><span>▤</span><b>{file.name}</b><small>{(file.size / 1024 / 1024).toFixed(2)} MB</small></div>)}</div>}
      <div className="form-grid two">
        {mode === "diagram" ? <label>Модель<select value={model} onChange={e => setModel(e.target.value)}>
          {visionModels.map(item => <option key={modelId(item)} value={modelId(item)}>{item.display_name}</option>)}
        </select></label> : <label className="toggle-line"><input type="checkbox" checked={noFilter} onChange={e => setNoFilter(e.target.checked)} /><span><b>Оставить шум</b><small>Не удалять номера страниц и колонтитулы</small></span></label>}
        <div className="action-slot"><button className="primary wide" disabled={!files.length || busy} onClick={run}>{busy ? "Обрабатываем…" : `Конвертировать ${files.length || ""}`} <span>→</span></button></div>
      </div>
    </section>
    {results.length > 0 && <section className="card result-card"><div className="card-head"><div><p className="eyebrow">Готово</p><h3>Результаты</h3></div></div>
      {results.map(result => <div className="result-row" key={result.filename}><span className="success-mark">✓</span><div><b>{result.archive_filename || result.filename}</b><small>{result.markdown.length.toLocaleString("ru-RU")} символов{result.archive_filename ? " · изображения включены" : ""}</small></div><button className="ghost" onClick={() => download(result)}>Скачать {result.archive_filename ? ".zip" : ".md"}</button></div>)}
    </section>}
  </div>;
}

function Catalog({ models, providers, submit, busy }: { models: Model[]; providers: Provider[]; submit: Function; busy: boolean }) {
  const [tab, setTab] = useState<"models" | "providers">("models");
  const [show, setShow] = useState(false);
  return <div className="content">
    <div className="section-toolbar"><div className="segmented small"><button className={tab === "models" ? "selected" : ""} onClick={() => setTab("models")}>Модели · {models.length}</button><button className={tab === "providers" ? "selected" : ""} onClick={() => setTab("providers")}>Провайдеры · {providers.length}</button></div><button className="primary compact" onClick={() => setShow(!show)}>+ Добавить</button></div>
    {show && (tab === "models" ? <ModelForm providers={providers} submit={submit} busy={busy} close={() => setShow(false)} /> : <ProviderForm submit={submit} busy={busy} close={() => setShow(false)} />)}
    {tab === "models" ? <div className="catalog-grid">{models.map(model => <article className="catalog-card" key={modelId(model)}>
      <div className="catalog-top"><span className="provider-badge large">{model.provider_code[0].toUpperCase()}</span><span className={`state ${model.status}`}>{model.status}</span></div>
      <h3>{model.display_name}</h3><code>{modelId(model)}</code>
      <div className="capabilities">{model.capabilities.map(cap => <span key={cap}>{cap}</span>)}</div>
      <dl><div><dt>Контекст</dt><dd>{compact(model.context_window)}</dd></div><div><dt>RPM</dt><dd>{model.rpm || "—"}</dd></div><div><dt>RPD</dt><dd>{model.rpd || "—"}</dd></div></dl>
    </article>)}</div> :
    <div className="table-card">{providers.map(provider => <div className="table-row" key={provider.code}><span className="provider-badge large">{provider.code[0].toUpperCase()}</span><div className="grow"><b>{provider.display_name}</b><code>{provider.code} · {provider.adapter}</code></div><span>{provider.secret_ref || "secret_ref не задан"}</span><span className={`state ${provider.enabled ? "active" : "disabled"}`}>{provider.enabled ? "active" : "disabled"}</span></div>)}</div>}
  </div>;
}

function ProviderForm({ submit, busy, close }: { submit: Function; busy: boolean; close: Function }) {
  const save = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); submit(() => api("/providers", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...data, enabled: true }) }), "Провайдер сохранён"); close(); };
  return <form className="card inline-form" onSubmit={save}><label>Код<input name="code" required placeholder="openai" /></label><label>Название<input name="display_name" required placeholder="OpenAI" /></label><label>Адаптер<input name="adapter" required placeholder="openai" /></label><label>Secret ref<input name="secret_ref" placeholder="env://OPENAI_API_KEY" /></label><button className="primary" disabled={busy}>Сохранить</button></form>;
}

function ModelForm({ providers, submit, busy, close }: { providers: Provider[]; submit: Function; busy: boolean; close: Function }) {
  const save = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); submit(() => api("/models", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...data, context_window: Number(data.context_window), max_output_tokens: Number(data.max_output_tokens) || null, rpm: Number(data.rpm) || null, tpm: Number(data.tpm) || null, rpd: Number(data.rpd) || null, capabilities: String(data.capabilities).split(",").map(x => x.trim()), status: "active" }) }), "Модель сохранена"); close(); };
  return <form className="card inline-form model-form" onSubmit={save}><label>Провайдер<select name="provider_code">{providers.map(p => <option key={p.code}>{p.code}</option>)}</select></label><label>Код модели<input name="code" required /></label><label>Название<input name="display_name" required /></label><label>Контекст<input name="context_window" type="number" min="1" required /></label><label>Макс. выход<input name="max_output_tokens" type="number" /></label><label>Возможности<input name="capabilities" defaultValue="text" /></label><label>RPM<input name="rpm" type="number" /></label><label>TPM<input name="tpm" type="number" /></label><label>RPD<input name="rpd" type="number" /></label><button className="primary" disabled={busy}>Сохранить</button></form>;
}

function Accounting({ dashboard, models, prices, budgets, submit, busy }: { dashboard: Dashboard | null; models: Model[]; prices: Price[]; budgets: Budget[]; submit: Function; busy: boolean }) {
  const [dialog, setDialog] = useState<"usage" | "price" | "budget" | null>(null);
  const totalRequests = Math.max(1, dashboard?.requests || 1);
  return <div className="content">
    <section className="metrics slim"><Metric label="Всего запросов" value={compact(dashboard?.requests || 0)} note={`${dashboard?.failed || 0} с ошибкой`} /><Metric label="Всего токенов" value={compact((dashboard?.input_tokens || 0) + (dashboard?.output_tokens || 0))} note="вход + выход" /><Metric label="Расходы" value={`${dashboard?.total_cost || 0} ${dashboard?.currency || "USD"}`} note="исторический итог" /></section>
    <div className="action-strip"><button className="primary compact" onClick={() => setDialog("usage")}>+ Записать usage</button><button className="ghost" onClick={() => setDialog("price")}>Добавить тариф</button><button className="ghost" onClick={() => setDialog("budget")}>Настроить бюджет</button></div>
    {dialog && <AccountingForm kind={dialog} models={models} submit={submit} busy={busy} close={() => setDialog(null)} />}
    <div className="grid-two account-grid"><section className="card"><div className="card-head"><div><p className="eyebrow">Распределение</p><h3>Запросы по моделям</h3></div></div>
      <div className="usage-list">{Object.entries(dashboard?.by_model || {}).map(([id, value]) => <div key={id}><div><b>{id}</b><span>{value.requests} · {value.cost} {dashboard?.currency}</span></div><div className="bar-track"><i style={{ width: `${Math.max(4, value.requests / totalRequests * 100)}%` }} /></div></div>)}{!dashboard?.requests && <Empty text="Записей usage пока нет" />}</div>
    </section><section className="card"><div className="card-head"><div><p className="eyebrow">Контроль</p><h3>Бюджеты</h3></div></div>
      <div className="budget-list">{budgets.map(b => <div key={b.scope}><span className="scope-icon">◎</span><div><b>{b.scope}</b><small>{b.period} · предупреждение {Number(b.warning_ratio) * 100}%</small></div><strong>{b.amount} {b.currency}</strong></div>)}{!budgets.length && <Empty text="Бюджеты не настроены" />}</div>
    </section></div>
    <section className="card"><div className="card-head"><div><p className="eyebrow">Актуальные ставки</p><h3>Тарифы моделей</h3></div><span className="step-pill">{prices.length} записей</span></div>
      <div className="price-table"><div className="price-row heading"><span>Модель</span><span>Вход / 1M</span><span>Выход / 1M</span><span>Валюта</span></div>{prices.map(price => <div className="price-row" key={price.model_id}><b>{price.model_id}</b><span>{price.input_per_million || "—"}</span><span>{price.output_per_million || "—"}</span><span>{price.currency}</span></div>)}</div>
    </section>
  </div>;
}

function AccountingForm({ kind, models, submit, busy, close }: { kind: "usage" | "price" | "budget"; models: Model[]; submit: Function; busy: boolean; close: Function }) {
  const save = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const raw = Object.fromEntries(new FormData(event.currentTarget)); let path = `/${kind === "usage" ? "usage" : kind === "price" ? "prices" : "budgets"}`; let data: Record<string, unknown> = raw;
    if (kind === "usage") data = { ...raw, input_tokens: Number(raw.input_tokens), output_tokens: Number(raw.output_tokens) || 0, cached_input_tokens: 0, reasoning_tokens: 0, image_count: 0, duration_ms: 0, status: "success", scope: raw.scope || "application" };
    if (kind === "budget") data = { ...raw, warning_ratio: "0.8", enabled: true };
    submit(() => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }), kind === "usage" ? "Usage записан" : kind === "price" ? "Тариф добавлен" : "Бюджет сохранён"); close(); };
  return <form className="card inline-form accounting-form" onSubmit={save}>
    {kind !== "budget" && <label>Модель<select name="model_id">{models.map(m => <option key={modelId(m)} value={modelId(m)}>{m.display_name}</option>)}</select></label>}
    {kind === "usage" && <><label>Операция<input name="operation" defaultValue="historical" /></label><label>Входные токены<input name="input_tokens" type="number" min="0" required /></label><label>Выходные токены<input name="output_tokens" type="number" min="0" defaultValue="0" /></label><label>Дата<input name="occurred_at" type="datetime-local" /></label><label>Scope<input name="scope" defaultValue="application" /></label></>}
    {kind === "price" && <><label>Вход / 1M<input name="input_per_million" inputMode="decimal" /></label><label>Выход / 1M<input name="output_per_million" inputMode="decimal" /></label><label>Кеш / 1M<input name="cached_input_per_million" inputMode="decimal" /></label><label>Изображение<input name="image_each" inputMode="decimal" /></label><label>Валюта<input name="currency" defaultValue="USD" /></label><input name="source" type="hidden" value="web-ui" /></>}
    {kind === "budget" && <><label>Scope<input name="scope" defaultValue="application" /></label><label>Лимит<input name="amount" required inputMode="decimal" /></label><label>Валюта<input name="currency" defaultValue="USD" /></label><label>Период<select name="period"><option value="daily">День</option><option value="monthly">Месяц</option><option value="total">Всё время</option></select></label></>}
    <button className="primary" disabled={busy}>Сохранить</button><button type="button" className="ghost" onClick={() => close()}>Отмена</button>
  </form>;
}

function Imports({ submit, busy }: { submit: Function; busy: boolean }) {
  const [config, setConfig] = useState<File | null>(null); const [usage, setUsage] = useState<File | null>(null);
  const upload = (path: string, file: File | null, message: string) => {
    if (!file) return; const body = new FormData(); body.append("file", file);
    submit(() => api(path, { method: "POST", body }), message);
  };
  return <div className="content narrow"><section className="intro-copy"><p className="eyebrow">Перенос данных</p><h2>Загрузите настройки<br/>и историю использования</h2><p>SQLite остаётся источником истины. Импорт проверяется до сохранения, а секретные значения отклоняются.</p></section>
    <div className="import-grid"><ImportCard symbol="⌘" title="Конфигурация моделей" text="Провайдеры, модели, лимиты, тарифы и бюджеты." accept=".yaml,.yml,.json" file={config} setFile={setConfig} action={() => upload("/config/import", config, "Конфигурация импортирована")} busy={busy} />
    <ImportCard symbol="⌁" title="История usage" text="Ранее выполненные запросы из CSV, JSON или JSONL." accept=".csv,.json,.jsonl,.ndjson" file={usage} setFile={setUsage} action={() => upload("/usage/import", usage, "История usage импортирована")} busy={busy} /></div>
    <section className="security-note"><span>⌾</span><div><b>Секреты остаются вне базы</b><p>Используйте ссылки вида <code>env://GEMINI_API_KEY</code>. Ключи, токены и пароли интерфейс не принимает.</p></div></section>
  </div>;
}

function ImportCard({ symbol, title, text, accept, file, setFile, action, busy }: { symbol: string; title: string; text: string; accept: string; file: File | null; setFile: (file: File | null) => void; action: () => void; busy: boolean }) {
  return <section className="card import-card"><span className="import-symbol">{symbol}</span><h3>{title}</h3><p>{text}</p><label className="file-pick"><input type="file" accept={accept} onChange={e => setFile(e.target.files?.[0] || null)} /><span>{file ? file.name : "Выбрать файл"}</span><b>Обзор</b></label><button className="primary wide" disabled={!file || busy} onClick={action}>Импортировать <span>→</span></button><small>Поддерживается: {accept.replaceAll(".", "").toUpperCase()}</small></section>;
}

function Empty({ text }: { text: string }) { return <div className="empty"><span>· · ·</span><p>{text}</p></div>; }
