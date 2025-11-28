import {Link} from "@nextui-org/react";

export default function HeaderLogo() {
  return (
    <Link className="block group" href="/" aria-label="Cruip">
      <svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
        <path className="fill-indigo-500" d="M13.853 18.14 1 10.643 31 1l-.019.058z" />
        <path className="fill-indigo-300" d="M13.853 18.14 30.981 1.058 21.357 31l-7.5-12.857z" />
      </svg>
    </Link>
  )
}
