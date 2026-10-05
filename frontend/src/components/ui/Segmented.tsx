interface SegmentedProps<T extends string | number> {
  label: string;
  options: readonly { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  name: string;
}

/** Radio group styled as a segmented control; keyboard works like native radios. */
export function Segmented<T extends string | number>({
  label,
  options,
  value,
  onChange,
  name,
}: SegmentedProps<T>) {
  return (
    <fieldset className="segmented">
      <legend className="sr-only">{label}</legend>
      {options.map((option) => {
        const id = `${name}-${String(option.value)}`;
        return (
          <label
            key={id}
            htmlFor={id}
            className={`segmented__option ${option.value === value ? "is-active" : ""}`}
          >
            <input
              id={id}
              type="radio"
              name={name}
              value={String(option.value)}
              checked={option.value === value}
              onChange={() => onChange(option.value)}
              className="sr-only"
            />
            {option.label}
          </label>
        );
      })}
    </fieldset>
  );
}
