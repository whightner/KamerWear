/** Address lines in the order a courier reads them. */
export function AddressDetails({
  address,
}: {
  address: {
    recipient_name: string;
    phone: string;
    region: string;
    city: string;
    quarter: string;
    landmark: string;
  };
}) {
  return (
    <address className="text-sm not-italic leading-relaxed text-muted">
      <span className="block font-medium text-ink">{address.recipient_name}</span>
      <span className="block">{address.landmark}</span>
      <span className="block">
        {address.quarter}, {address.city}
      </span>
      <span className="block">{address.region}, Cameroon</span>
      <span className="block">{address.phone}</span>
    </address>
  );
}
