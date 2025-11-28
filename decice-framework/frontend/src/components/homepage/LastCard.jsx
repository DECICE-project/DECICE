import {Avatar, Button, Card, CardBody, CardFooter, CardHeader, Image, Link} from "@nextui-org/react";


export default function Component(props) {
  return (
    <Card
      className="mt-7 overflow-none relative w-full border-small border-foreground/10 inset-0 bg-gradient-to-b from-indigo-100 to-white   "
      {...props}
    >
              <div className="hidden md:block absolute left-1/2 -translate-x-1/2 " aria-hidden="true">
        <Image src={"/hero-illustration.svg"} className="max-w-none" priority alt="Hero Illustration" />
      </div>
      <CardHeader>
        <div className="flex items-center gap-3">
          <Avatar
            className="border-small border-black/20 bg-transparent"
            icon={<Image  src={"/decice.png"}  />}
          />

          <p className="text-large font-medium font-nycd ">Decice Dashboard</p>
        </div>
      </CardHeader>
      <CardBody className="px-3">
        <div className="flex flex-col gap-2 px-2">
          <p className="text-large font-medium text-black/80">Enter Decice Job Dashboard</p>
          <p className="text-small text-black/60">
            Unlock the full power of Decice Dashboard! Gain expertise and insights from top organizations
            through guided tutorials, boosting productivity, enhancing security, and enabling
            seamless collaboration.
          </p>
        </div>
      </CardBody>
      <CardFooter className="justify-end gap-2">
        <Button as= {Link}  href="/signin" fullWidth  className="border-small border-secondary/20 bg-secondary/10 text-secondary-500">
          Enter Dashboard
        </Button>
      </CardFooter>
    </Card>
  );
}
