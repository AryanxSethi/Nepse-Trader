import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts'

interface Props {
  data: { value: number }[]
  color?: string
}

export default function MiniChart({ data }: Props) {
  const isUp = data.length > 1 && data[data.length - 1].value >= data[0].value
  return (
    <ResponsiveContainer width={100} height={32}>
      <LineChart data={data}>
        <YAxis domain={['dataMin', 'dataMax']} hide />
        <Line
          type="monotone"
          dataKey="value"
          stroke={isUp ? '#22c55e' : '#ef4444'}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={true}
          animationDuration={800}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
