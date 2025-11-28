import React from "react";

import {cn} from "../cn";

import Review from "./review";

const CardReview = React.forwardRef(({className, ...review}, ref) => (
  <div ref={ref} className={cn("rounded-medium bg-content1 p-5 shadow-small", className)}>
    <Review {...review} />
  </div>
));

CardReview.displayName = "CardReview";

export default CardReview;
