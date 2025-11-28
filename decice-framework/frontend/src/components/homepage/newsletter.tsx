export default function Newsletter() {
  return (
    <div className="relative text-center px-4 py-6 group">
      <div
        className="absolute inset-0 rounded-xl bg-gray-50 border border-gray-200 -rotate-1 group-hover:rotate-0 transition duration-150 ease-in-out -z-10"
        aria-hidden="true"
      />
      <div className="font-nycd text-xl text-indigo-500 mb-1">Land your dream job</div>
      <div className="text-2xl font-bold mb-5">Get a weekly email with the latest startup jobs.</div>
      <form className="inline-flex max-w-sm">
        <div className="flex flex-col sm:flex-row justify-center max-w-xs mx-auto sm:max-w-none">
          <input type="email" className="form-input py-1.5 w-full mb-2 sm:mb-0 sm:mr-2" placeholder="Your email" aria-label="Your email" />
          <button className="btn-sm text-white bg-indigo-500 hover:bg-indigo-600 shadow-sm whitespace-nowrap" type="submit">
            Join Newsletter
          </button>
        </div>
      </form>
    </div>
  )
}
