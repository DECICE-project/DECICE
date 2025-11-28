
import Hero from './hero'
import Header from './header'
import Footer from './footer'
import SideArea from "./sideArea";
import LastCard from "./LastCard";
import News  from "./News";

export default function Home() {
  return (
    <>
    <div className=" flex flex-col min-h-screen overflow-hidden supports-[overflow:clip]:overflow-clip">
    <Header />
  <main className=" grow">
    <Hero/>

    <section>
    <div className=" max-w-7xl mx-auto px-4 sm:px-6">
      <div className="py-8 md:py-16">
        <div className="flex flex-col md:flex-row md:justify-between" data-sticky-container>
          {/* SideArea */}
          <div className="w-full md:max-w-80 md:order-2 md:ml-7">
            <SideArea/>
          </div>
 {/* Main content */}
 <News/>

        </div>
        <LastCard/>
      </div>
    </div>
  </section>
  </main>
  <Footer />
    </div>


</>
  )
}
