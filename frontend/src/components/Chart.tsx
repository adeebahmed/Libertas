import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

type Formatter = (value: number) => string

type Series = {
  dataKey: string
  name?: string
  stroke?: string
  strokeDasharray?: string
  strokeWidth?: number
}

type Reference = {
  y: number
  label?: string
}

const chartMargin = { top: 4, right: 4, left: -4, bottom: 0 }

function TerminalTooltip({ active, payload, label, formatter }: any & { formatter?: Formatter }) {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-label">{label}</div>
      {payload.map((item: any) => (
        <div key={item.name ?? item.dataKey} style={{ color: item.color ?? 'var(--text)' }}>
          {(item.name ?? item.dataKey) as string}: {formatter ? formatter(Number(item.value)) : item.value}
        </div>
      ))}
    </div>
  )
}

function ChartAxes({ xKey, formatter }: { xKey: string; formatter?: Formatter }) {
  return (
    <>
      <XAxis dataKey={xKey} tick={{ fill: 'var(--text-3)', fontSize: 'var(--fs-xs)' }} axisLine={false} tickLine={false} minTickGap={18} />
      <YAxis
        tick={{ fill: 'var(--text-3)', fontSize: 'var(--fs-xs)' }}
        axisLine={false}
        tickLine={false}
        tickCount={4}
        tickFormatter={formatter}
      />
      <ReferenceLine y={0} stroke="var(--border)" strokeWidth={1} />
    </>
  )
}

export function TerminalLineChart({
  data,
  series,
  height = 320,
  xKey = 'year',
  formatter,
  reference,
}: {
  data: any[]
  series: Series[]
  height?: number
  xKey?: string
  formatter?: Formatter
  reference?: Reference
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={chartMargin}>
        <ChartAxes xKey={xKey} formatter={formatter} />
        {reference && (
          <ReferenceLine
            y={reference.y}
            stroke="var(--accent)"
            strokeDasharray="4 2"
            label={{ value: reference.label, fill: 'var(--accent)', fontSize: 'var(--fs-xs)' }}
          />
        )}
        <Tooltip content={<TerminalTooltip formatter={formatter} />} cursor={{ stroke: 'var(--border-strong)', strokeWidth: 1 }} />
        {series.map((item) => (
          <Line
            key={item.dataKey}
            type="monotone"
            dataKey={item.dataKey}
            name={item.name ?? item.dataKey}
            stroke={item.stroke ?? 'var(--text)'}
            strokeWidth={item.strokeWidth ?? 1.5}
            strokeDasharray={item.strokeDasharray}
            dot={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

export function TerminalAreaChart({
  data,
  dataKey,
  height = 280,
  xKey = 'date',
  formatter,
}: {
  data: any[]
  dataKey: string
  height?: number
  xKey?: string
  formatter?: Formatter
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={chartMargin}>
        <defs>
          <linearGradient id="terminalAreaFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--text)" stopOpacity={0.14} />
            <stop offset="95%" stopColor="var(--text)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <ChartAxes xKey={xKey} formatter={formatter} />
        <Tooltip content={<TerminalTooltip formatter={formatter} />} cursor={{ stroke: 'var(--border-strong)', strokeWidth: 1 }} />
        <Area type="monotone" dataKey={dataKey} stroke="var(--text)" strokeWidth={1.5} fill="url(#terminalAreaFill)" dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function TerminalBarChart({
  data,
  dataKey,
  height = 220,
  xKey = 'name',
  formatter,
}: {
  data: Array<Record<string, any>>
  dataKey: string
  height?: number
  xKey?: string
  formatter?: Formatter
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={chartMargin} barCategoryGap="30%">
        <ChartAxes xKey={xKey} formatter={formatter} />
        <Tooltip content={<TerminalTooltip formatter={formatter} />} cursor={{ fill: 'var(--bg-1)' }} />
        <Bar dataKey={dataKey} radius={[2, 2, 0, 0]}>
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.fill ?? 'var(--text)'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export function TerminalDonut({
  data,
  colors,
  size = 170,
}: {
  data: { name: string; value: number }[]
  colors: string[]
  size?: number
}) {
  const total = data.reduce((sum, item) => sum + item.value, 0)
  const radius = size / 2 - 12
  const circumference = 2 * Math.PI * radius
  let offset = 0

  return (
    <svg className="terminal-donut" width="100%" height={size} viewBox={`0 0 ${size} ${size}`} role="img">
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--border)" strokeWidth={8} />
      {data.map((item, index) => {
        const length = total ? (item.value / total) * circumference : 0
        const dash = `${length} ${circumference - length}`
        const segment = (
          <circle
            key={item.name}
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={colors[index % colors.length]}
            strokeWidth={8}
            strokeDasharray={dash}
            strokeDashoffset={-offset}
            strokeLinecap="butt"
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
          />
        )
        offset += length
        return segment
      })}
    </svg>
  )
}
