export type Language = 'pt' | 'en';
export type Timeframe = '1D' | '1W' | '1M' | '1Y';

export interface TimeframeData {
  points: number[];
  dates: string[];
  spreadChange: string;
  sharpe: string;
  var99: string;
  volume: string;
  activeFactor: string;
}

export interface AlphaModel {
  id: 'liquidity' | 'regime' | 'factorDrift';
  name: string;
  tag: string;
  alphaSpread: string;
  sharpe: string;
  confidence: string;
  latency: string;
  description: string;
  dataPoints: number[];
  factors: { name: string; weight: string; delta: string }[];
}

export interface MacroScenario {
  id: 'inflation' | 'liquidity' | 'rates' | 'equilibrium';
  name: string;
  description: string;
  alphaImpact: string;
  portfolioDrawdown: string;
  regimeState: string;
  hedgingAction: string;
  curveImpact: number[];
}

export interface MetricItem {
  label: string;
  value: string;
  change: string;
  benchmark: string;
  subtext: string;
}

export interface BentoCardData {
  number: string;
  title: string;
  subtitle: string;
  description: string;
  tag: string;
  bullets: string[];
  metricHighlight: { value: string; label: string };
  microChartType: 'bars' | 'matrix' | 'curve';
  dataPoints: number[];
}

export interface TranslationDictionary {
  demoNotice: string;
  nav: {
    capabilities: string;
    cockpit: string;
    alternativeAlpha: string;
    simulator: string;
    performance: string;
    accessSystem: string;
    systemLive: string;
  };
  hero: {
    kicker: string;
    titleLine1: string;
    titleLine2: string;
    subtitle: string;
    ctaPrimary: string;
    ctaSecondary: string;
    terminalBadge: string;
  };
  cockpit: {
    title: string;
    feedLabel: string;
    spreadLabel: string;
    sharpeLabel: string;
    varLabel: string;
    factorComposition: string;
    inspectHint: string;
    launchConsole: string;
  };
  tickerStrip: {
    title: string;
    items: MetricItem[];
  };
  capabilities: {
    sectionTag: string;
    title: string;
    subtitle: string;
    items: BentoCardData[];
  };
  alternativeAlpha: {
    sectionTag: string;
    title: string;
    description: string;
    modelSelectorLabel: string;
    signalSpread: string;
    sharpeRatio: string;
    confidenceScore: string;
    executionLatency: string;
    historicalYield: string;
    activeWeights: string;
    terminalAction: string;
  };
  simulator: {
    sectionTag: string;
    title: string;
    description: string;
    scenarioLabel: string;
    projectedSpread: string;
    maxDrawdown: string;
    regimeIndicator: string;
    hedgingRecommendation: string;
    testNotice: string;
    simulatedCurveTitle: string;
  };
  proof: {
    sectionTag: string;
    title: string;
    subtitle: string;
    stats: { value: string; label: string; detail: string }[];
  };
  ctaBanner: {
    title: string;
    description: string;
    button: string;
    dockerInfo: string;
    deploymentBadge: string;
  };
  footer: {
    tagline: string;
    institutionalNotice: string;
    copyright: string;
    quickLinksTitle: string;
    legalTitle: string;
    terms: string;
    privacy: string;
    disclaimer: string;
  };
}
