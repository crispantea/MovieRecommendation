export default function InputField({ label, type, value, onChange }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <label>{label}</label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        style={{ width: '100%', padding: 8 }}
      />
    </div>
  )
}