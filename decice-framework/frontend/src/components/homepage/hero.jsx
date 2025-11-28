
import {Image} from "@nextui-org/react";
export default function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* Bg */}
      <div className="absolute inset-0 bg-gradient-to-b from-indigo-100 to-white dark:to-black pointer-events-none -z-10" aria-hidden="true" />

      {/* Illustration */}
      <div className="hidden md:block absolute left-1/2 -translate-x-1/2 pointer-events-none -z-10" aria-hidden="true">
        <Image src={"/hero-illustration.svg"} className="max-w-none" priority alt="Hero Illustration" />
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="pt-28 pb-8 md:pt-36 md:pb-16">
          {/* Hero content */}
          <div className="max-w-3xl text-center md:text-left">
            {/* Copy */}
            <h1 className="text-4xl sm:text-6xl font-semibold	 font-inter mb-6 dark:text-white">
            Intelligent Collaboration  Framework  <span className="font-nycd text-indigo-500 font-normal"></span>
            </h1>
            <p className="text-lg text-gray-500 mb-8 dark:text-white">
            Welcome to Decice Dashboard designed for the decice API.
              <br className="hidden md:block" />If you have an individual registration, you can log in.
            </p>
            {/* Button + Avatars */}
            <div className="sm:flex sm:items-center sm:justify-center md:justify-start space-y-6 sm:space-y-0 sm:space-x-5">

                <div>
        <a className="inline-flex justify-center whitespace-nowrap rounded-lg px-3.5 py-2.5 text-sm font-medium text-slate-200 dark:text-slate-800 bg-gradient-to-r from-slate-800 to-slate-700 dark:from-slate-200 dark:to-slate-100 dark:hover:bg-slate-100 shadow focus:outline-none focus:ring focus:ring-slate-500/50 focus-visible:outline-none focus-visible:ring focus-visible:ring-slate-500/50 relative before:absolute before:inset-0 before:rounded-[inherit] before:bg-[linear-gradient(45deg,transparent_25%,theme(colors.white/.5)_50%,transparent_75%,transparent_100%)] dark:before:bg-[linear-gradient(45deg,transparent_25%,theme(colors.white)_50%,transparent_75%,transparent_100%)] before:bg-[length:250%_250%,100%_100%] before:bg-[position:200%_0,0_0] before:bg-no-repeat before:[transition:background-position_0s_ease] hover:before:bg-[position:-100%_0,0_0] hover:before:duration-[1500ms]" href="/signin">Enter Dashboard</a>
    </div>

              <div className="sm:flex sm:items-center sm:justify-center space-y-2 sm:space-y-0 sm:space-x-3">
                <div className="inline-flex -space-x-3 -ml-0.5">
                  <Image
                    className="rounded-md border-2 border-indigo-50 box-content"
                    src={"https://www.decice.eu/wp-content/uploads/2022/09/09-Marmara-University-1-Logo-200x126-1.png"}
                    width={32}
                    height={32}
                    alt="Marmara University"
                  />
                  <Image
                    className="rounded-md border-2 border-indigo-50 box-content"
                    src={"https://www.decice.eu/wp-content/uploads/2022/09/04-KUNGLIGA-TEKNISKA-HOEGSKOLAN-1-Logo-200x126-1.png"}
                    width={32}
                    height={32}
                    alt="KTH"
                  />
                  <Image
                    className="rounded-md border-2 border-indigo-50 box-content"
                    src={"https://www.decice.eu/wp-content/uploads/2022/09/11-unibo-Logo-200x126-1.png"}
                    width={32}
                    height={32}
                    alt="UNIBO"
                  />
                  <Image
                    className="rounded-md border-2 border-indigo-50 box-content"
                    src={"https://www.decice.eu/wp-content/uploads/2022/09/06-Huawei-Logo-200x126-1.png"}
                    width={32}
                    height={32}
                    alt="Huawei"
                  />
                </div>
                <a
                  href="https://www.decice.eu/consortium/"
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-gray-500 font-medium dark:text-white hover:text-indigo-500 underline-offset-2 hover:underline"
                >
                  Reach consortium members
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
