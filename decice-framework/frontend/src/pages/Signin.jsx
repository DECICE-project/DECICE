import Signin from "../components/signin/Signin";
import {Image} from "@nextui-org/react";
import CookiesPop from "../components/cookies/CookiesPop"
import ServerPopUp from "../components/serverStatus/ServerPopUp.tsx"
export default function AuthLayout() {
  return (
    <>
         <body
        className={` dark:bg-[#1E201E] bg-gray-50 font-inter tracking-tight text-gray-900 antialiased`}
      >
        <div className="flex min-h-screen flex-col overflow-hidden supports-[overflow:clip]:overflow-clip">

        <header className="absolute z-30 w-full">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="flex h-16 items-center justify-between md:h-20">
            {/* Site branding */}
            <div className="mr-4 shrink-0">
              <a href="/" aria-label="Go to homepage">
                <Image src="/decice.png" width={70} alt="Decice logo" />
              </a>
            </div>
          </div>
        </div>
      </header>

      <main className="relative flex grow">
        <div
          className="pointer-events-none absolute bottom-0 left-0 -translate-x-1/3"
          aria-hidden="true"
        >
          <div className="h-80 w-80 rounded-full bg-gradient-to-tr from-blue-500 opacity-70 blur-[160px]"></div>
        </div>

        {/* Content */}
        <div className="w-full">
          <div className="flex h-full flex-col justify-center before:min-h-[4rem] before:flex-1 after:flex-1 md:before:min-h-[5rem]">
            <div className="px-4 sm:px-6">
              <div className="mx-auto w-full max-w-sm">
                <div className="py-16 md:py-20">
                <Signin/>
                </div>
              </div>
            </div>
          </div>
        </div>

        <>
          {/* Right side */}
          <div className="relative my-6 mr-6 hidden w-[572px] shrink-0 overflow-hidden rounded-3xl lg:block">
  {/* Background */}
  <div
    className="absolute inset-0 bg-gradient-to-b from-indigo-300 to-white"
    aria-hidden="true"
  >
    <Image
      src="/auth-illustration.svg"
      className="max-w-none"
      height={2400}
      alt="Auth bg"
      style={{ opacity: 0.3 }}
    />
  </div>
  {/* Logo */}
  <div className="absolute bottom-4 left-1/2 z-10">
    <Image src="/decice.png" width={300} alt="logo" />
  </div>
            {/* Illustration */}
            <div className="absolute left-32 top-1/2 w-[500px] -translate-y-1/2 ">
              <div className="aspect-video w-full rounded-2xl bg-gray-900 px-5 py-3 shadow-xl transition duration-300">
                <div className="relative mb-8 flex items-center justify-between before:block before:h-[9px] before:w-[41px] before:bg-[length:16px_9px] before:[background-image:radial-gradient(circle_at_4.5px_4.5px,_theme(colors.gray.600)_4.5px,_transparent_0)] after:w-[41px]">
                  <span className="text-[13px] font-medium text-white">
                    decice.eu
                  </span>
                </div>
                <div className="font-mono text-sm text-gray-500 transition duration-300 [&_span]:opacity-0">
                  <span className="animate-[code-1_10s_infinite] text-gray-200">
                  kubectl get decicejobs.dev.decice.com
                  </span>{" "}
                  <br />
                  <span className="animate-[code-2_10s_infinite]">
                  NAME              AGE
                  </span>{" "}
                  <br />
                  <span className="animate-[code-2_10s_infinite]">
                  user-job-0         1h
                  </span>{" "}
                  <br />
                  <span className="animate-[code-2_10s_infinite]">
                  user2-job-0         2h
                  </span>{" "}
                  <br />
                </div>
              </div>
            </div>
          </div>
        </>
      </main>


        </div>
        {localStorage.getItem("cookieSettings") ? null: <CookiesPop/>}
        <ServerPopUp/>
      </body>



    </>
  );
}
