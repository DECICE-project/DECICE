import {Image, Button, Link} from "@nextui-org/react";

export default function Header() {
  return (
    <header className="absolute w-full z-30">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16 md:h-20">
          {/* Site branding */}
          <div className="shrink-0 mr-4">
            <Image src={"/decice.png"} width={70}/>
          </div>

          {/* Desktop navigation */}
          <nav className="flex grow">
            {/* Desktop sign in links */}
            <ul className="flex grow justify-end flex-wrap items-center">
              <li className="ml-3">
                <Button as= {Link} href="/signin" className="btn-sm text-white bg-indigo-500 hover:bg-indigo-600 w-full shadow-sm" >
                  Enter Dashboard
                </Button>
              </li>
            </ul>
          </nav>
        </div>
      </div>
    </header>
  )
}
