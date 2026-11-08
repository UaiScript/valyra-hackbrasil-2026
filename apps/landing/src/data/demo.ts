// Static synthetic examples only. This page makes no financial calculations or forecasts.
import type { Timeframe, TimeframeData, Language, AlphaModel, MacroScenario } from '../types/content';

export const COCKPIT_TIMEFRAMES: Record<Timeframe, TimeframeData> = {
  '1D': {
    points: [100.0, 100.4, 100.8, 100.5, 101.2, 101.9, 101.6, 102.4, 102.9, 102.7, 103.5, 104.1],
    dates: Array.from({ length: 12 }, (_, i) => `Demo ${i + 1}`),
    spreadChange: '+41.2 bps',
    sharpe: '2.84',
    var99: '0.84%',
    volume: 'Demo',
    activeFactor: 'Demo',
  },
  '1W': {
    points: [98.2, 99.5, 99.1, 101.0, 102.3, 101.8, 103.5, 104.9, 104.2, 105.8, 106.7, 107.8],
    dates: Array.from({ length: 12 }, (_, i) => `Demo ${i + 1}`),
    spreadChange: '+96.0 bps',
    sharpe: '2.72',
    var99: '1.42%',
    volume: 'Demo',
    activeFactor: 'Demo',
  },
  '1M': {
    points: [94.0, 95.8, 97.2, 96.5, 99.1, 101.4, 103.2, 102.8, 105.6, 108.1, 109.8, 112.4],
    dates: Array.from({ length: 12 }, (_, i) => `Demo ${i + 1}`),
    spreadChange: '+184 bps',
    sharpe: '2.68',
    var99: '2.15%',
    volume: 'Demo',
    activeFactor: 'Demo',
  },
  '1Y': {
    points: [82.0, 86.5, 89.2, 93.0, 91.5, 96.8, 101.2, 105.4, 110.1, 115.8, 121.4, 128.6],
    dates: Array.from({ length: 12 }, (_, i) => `Demo ${i + 1}`),
    spreadChange: '+466 bps',
    sharpe: '2.41',
    var99: '4.12%',
    volume: 'Demo',
    activeFactor: 'Demo',
  },
};


// All numeric series are static, synthetic display data; no predictive model runs here.
export const ALPHA_MODELS: Record<Language, AlphaModel[]> = {
  "pt": [
    {
      "id": "liquidity",
      "name": "Clima e produção",
      "tag": "DEMO",
      "alphaSpread": "+4.18%",
      "sharpe": "2.68",
      "confidence": "98.4%",
      "latency": "Estática",
      "description": "Série sintética para explorar a interface; sem dados observados ou modelo validado.",
      "dataPoints": [
        22,
        28,
        35,
        41,
        38,
        52,
        60,
        58,
        71,
        79,
        86,
        94
      ],
      "factors": [
        {
          "name": "Exemplo A",
          "weight": "38%",
          "delta": "Demo"
        },
        {
          "name": "Exemplo B",
          "weight": "32%",
          "delta": "Demo"
        },
        {
          "name": "Exemplo C",
          "weight": "30%",
          "delta": "Demo"
        }
      ]
    },
    {
      "id": "regime",
      "name": "Comércio exterior",
      "tag": "DEMO",
      "alphaSpread": "+3.92%",
      "sharpe": "2.35",
      "confidence": "95.1%",
      "latency": "Estática",
      "description": "Série sintética para explorar a interface; sem dados observados ou modelo validado.",
      "dataPoints": [
        18,
        24,
        30,
        28,
        44,
        49,
        55,
        62,
        60,
        74,
        82,
        89
      ],
      "factors": [
        {
          "name": "Exemplo A",
          "weight": "38%",
          "delta": "Demo"
        },
        {
          "name": "Exemplo B",
          "weight": "32%",
          "delta": "Demo"
        },
        {
          "name": "Exemplo C",
          "weight": "30%",
          "delta": "Demo"
        }
      ]
    },
    {
      "id": "factorDrift",
      "name": "Contexto de preços",
      "tag": "DEMO",
      "alphaSpread": "+3.45%",
      "sharpe": "2.19",
      "confidence": "96.7%",
      "latency": "Estática",
      "description": "Série sintética para explorar a interface; sem dados observados ou modelo validado.",
      "dataPoints": [
        15,
        20,
        27,
        34,
        41,
        46,
        51,
        57,
        66,
        73,
        78,
        84
      ],
      "factors": [
        {
          "name": "Exemplo A",
          "weight": "38%",
          "delta": "Demo"
        },
        {
          "name": "Exemplo B",
          "weight": "32%",
          "delta": "Demo"
        },
        {
          "name": "Exemplo C",
          "weight": "30%",
          "delta": "Demo"
        }
      ]
    }
  ],
  "en": [
    {
      "id": "liquidity",
      "name": "Weather and production",
      "tag": "DEMO",
      "alphaSpread": "+4.18%",
      "sharpe": "2.68",
      "confidence": "98.4%",
      "latency": "Static",
      "description": "Synthetic series for exploring the interface; no observed data or validated model.",
      "dataPoints": [
        22,
        28,
        35,
        41,
        38,
        52,
        60,
        58,
        71,
        79,
        86,
        94
      ],
      "factors": [
        {
          "name": "Example A",
          "weight": "38%",
          "delta": "Demo"
        },
        {
          "name": "Example B",
          "weight": "32%",
          "delta": "Demo"
        },
        {
          "name": "Example C",
          "weight": "30%",
          "delta": "Demo"
        }
      ]
    },
    {
      "id": "regime",
      "name": "Foreign trade",
      "tag": "DEMO",
      "alphaSpread": "+3.92%",
      "sharpe": "2.35",
      "confidence": "95.1%",
      "latency": "Static",
      "description": "Synthetic series for exploring the interface; no observed data or validated model.",
      "dataPoints": [
        18,
        24,
        30,
        28,
        44,
        49,
        55,
        62,
        60,
        74,
        82,
        89
      ],
      "factors": [
        {
          "name": "Example A",
          "weight": "38%",
          "delta": "Demo"
        },
        {
          "name": "Example B",
          "weight": "32%",
          "delta": "Demo"
        },
        {
          "name": "Example C",
          "weight": "30%",
          "delta": "Demo"
        }
      ]
    },
    {
      "id": "factorDrift",
      "name": "Price context",
      "tag": "DEMO",
      "alphaSpread": "+3.45%",
      "sharpe": "2.19",
      "confidence": "96.7%",
      "latency": "Static",
      "description": "Synthetic series for exploring the interface; no observed data or validated model.",
      "dataPoints": [
        15,
        20,
        27,
        34,
        41,
        46,
        51,
        57,
        66,
        73,
        78,
        84
      ],
      "factors": [
        {
          "name": "Example A",
          "weight": "38%",
          "delta": "Demo"
        },
        {
          "name": "Example B",
          "weight": "32%",
          "delta": "Demo"
        },
        {
          "name": "Example C",
          "weight": "30%",
          "delta": "Demo"
        }
      ]
    }
  ]
};
export const MACRO_SCENARIOS: Record<Language, MacroScenario[]> = {
  "pt": [
    {
      "id": "inflation",
      "name": "Inflação ilustrativa",
      "description": "Contexto fictício para demonstrar a navegação entre cenários.",
      "alphaImpact": "+4.85%",
      "portfolioDrawdown": "-1.82%",
      "regimeState": "Inflação ilustrativa",
      "hedgingAction": "Quais fontes e premissas sustentariam uma análise deste cenário?",
      "curveImpact": [
        100,
        99,
        98,
        101,
        103
      ]
    },
    {
      "id": "liquidity",
      "name": "Liquidez ilustrativa",
      "description": "Contexto fictício para demonstrar a navegação entre cenários.",
      "alphaImpact": "+5.12%",
      "portfolioDrawdown": "-2.10%",
      "regimeState": "Liquidez ilustrativa",
      "hedgingAction": "Quais fontes e premissas sustentariam uma análise deste cenário?",
      "curveImpact": [
        100,
        99,
        98,
        101,
        103
      ]
    },
    {
      "id": "rates",
      "name": "Juros ilustrativos",
      "description": "Contexto fictício para demonstrar a navegação entre cenários.",
      "alphaImpact": "+3.72%",
      "portfolioDrawdown": "-1.45%",
      "regimeState": "Juros ilustrativos",
      "hedgingAction": "Quais fontes e premissas sustentariam uma análise deste cenário?",
      "curveImpact": [
        100,
        99,
        98,
        101,
        103
      ]
    },
    {
      "id": "equilibrium",
      "name": "Equilíbrio ilustrativo",
      "description": "Contexto fictício para demonstrar a navegação entre cenários.",
      "alphaImpact": "+3.20%",
      "portfolioDrawdown": "-0.65%",
      "regimeState": "Equilíbrio ilustrativo",
      "hedgingAction": "Quais fontes e premissas sustentariam uma análise deste cenário?",
      "curveImpact": [
        100,
        99,
        98,
        101,
        103
      ]
    }
  ],
  "en": [
    {
      "id": "inflation",
      "name": "Sample inflation",
      "description": "Fictional context to demonstrate switching between scenarios.",
      "alphaImpact": "+4.85%",
      "portfolioDrawdown": "-1.82%",
      "regimeState": "Sample inflation",
      "hedgingAction": "Which sources and assumptions would support an analysis of this scenario?",
      "curveImpact": [
        100,
        99,
        98,
        101,
        103
      ]
    },
    {
      "id": "liquidity",
      "name": "Sample liquidity",
      "description": "Fictional context to demonstrate switching between scenarios.",
      "alphaImpact": "+5.12%",
      "portfolioDrawdown": "-2.10%",
      "regimeState": "Sample liquidity",
      "hedgingAction": "Which sources and assumptions would support an analysis of this scenario?",
      "curveImpact": [
        100,
        99,
        98,
        101,
        103
      ]
    },
    {
      "id": "rates",
      "name": "Sample interest rates",
      "description": "Fictional context to demonstrate switching between scenarios.",
      "alphaImpact": "+3.72%",
      "portfolioDrawdown": "-1.45%",
      "regimeState": "Sample interest rates",
      "hedgingAction": "Which sources and assumptions would support an analysis of this scenario?",
      "curveImpact": [
        100,
        99,
        98,
        101,
        103
      ]
    },
    {
      "id": "equilibrium",
      "name": "Sample equilibrium",
      "description": "Fictional context to demonstrate switching between scenarios.",
      "alphaImpact": "+3.20%",
      "portfolioDrawdown": "-0.65%",
      "regimeState": "Sample equilibrium",
      "hedgingAction": "Which sources and assumptions would support an analysis of this scenario?",
      "curveImpact": [
        100,
        99,
        98,
        101,
        103
      ]
    }
  ]
};
