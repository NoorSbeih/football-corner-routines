import Link from "next/link";

export default function NotFound() {
  return (
    <div className="wrap">
      <h1>That page is not in the tournament</h1>
      <p>
        <Link href="/">Back to the teams</Link>
      </p>
    </div>
  );
}
