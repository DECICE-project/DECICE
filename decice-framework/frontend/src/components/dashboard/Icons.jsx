export const GalleryIcon = (props) => (
    <svg
      aria-hidden="true"
      focusable="false"
      height="24"
      role="presentation"
      viewBox="0 0 24 24"
      width="24"
      fill="none"
      {...props}
    >
      <path d="M2.58078 19.0112L2.56078 19.0312C2.29078 18.4413 2.12078 17.7713 2.05078 17.0312C2.12078 17.7613 2.31078 18.4212 2.58078 19.0112Z" fill="currentColor"/>
      <path d="M9.00109 10.3811C10.3155 10.3811 11.3811 9.31553 11.3811 8.00109C11.3811 6.68666 10.3155 5.62109 9.00109 5.62109C7.68666 5.62109 6.62109 6.68666 6.62109 8.00109C6.62109 9.31553 7.68666 10.3811 9.00109 10.3811Z" fill="currentColor"/>
      <path d="M16.19 2H7.81C4.17 2 2 4.17 2 7.81V16.19C2 17.28 2.19 18.23 2.56 19.03C3.42 20.93 5.26 22 7.81 22H16.19C19.83 22 22 19.83 22 16.19V13.9V7.81C22 4.17 19.83 2 16.19 2ZM20.37 12.5C19.59 11.83 18.33 11.83 17.55 12.5L13.39 16.07C12.61 16.74 11.35 16.74 10.57 16.07L10.23 15.79C9.52 15.17 8.39 15.11 7.59 15.65L3.85 18.16C3.63 17.6 3.5 16.95 3.5 16.19V7.81C3.5 4.99 4.99 3.5 7.81 3.5H16.19C19.01 3.5 20.5 4.99 20.5 7.81V12.61L20.37 12.5Z" fill="currentColor"/>
    </svg>
  );


  export const MusicIcon = (props) => (
    <svg
      aria-hidden="true"
      focusable="false"
      height="24"
      role="presentation"
      viewBox="0 0 24 24"
      width="24"
      fill="none"
      {...props}
    >
      <path d="M9.66984 13.9219C8.92984 13.9219 8.33984 14.5219 8.33984 15.2619C8.33984 16.0019 8.93984 16.5919 9.66984 16.5919C10.4098 16.5919 11.0098 15.9919 11.0098 15.2619C11.0098 14.5219 10.4098 13.9219 9.66984 13.9219Z" fill="currentColor"/>
      <path d="M16.19 2H7.81C4.17 2 2 4.17 2 7.81V16.18C2 19.83 4.17 22 7.81 22H16.18C19.82 22 21.99 19.83 21.99 16.19V7.81C22 4.17 19.83 2 16.19 2ZM17.12 9.8C17.12 10.41 16.86 10.95 16.42 11.27C16.14 11.47 15.8 11.58 15.44 11.58C15.23 11.58 15.02 11.54 14.8 11.47L12.51 10.71C12.5 10.71 12.48 10.7 12.47 10.69V15.25C12.47 16.79 11.21 18.05 9.67 18.05C8.13 18.05 6.87 16.79 6.87 15.25C6.87 13.71 8.13 12.45 9.67 12.45C10.16 12.45 10.61 12.59 11.01 12.8V8.63V8.02C11.01 7.41 11.27 6.87 11.71 6.55C12.16 6.23 12.75 6.15 13.33 6.35L15.62 7.11C16.48 7.4 17.13 8.3 17.13 9.2V9.8H17.12Z" fill="currentColor"/>
    </svg>
  );


  export function VideoIcon(props) {
    const fill = props.fill || 'currentColor';
    const secondaryfill = props.secondaryfill || fill;
    const strokewidth = props.strokewidth || 3;
    const width = props.width || '1.5em';
    const height = props.height || '1.5em';

    return (
      <svg height={height} width={width} viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
    <g fill={fill} strokeLinecap="butt" strokeLinejoin="miter">
      <polyline fill="none" points=" 17,9 17,3 31,3 31,9 " stroke={secondaryfill} strokeLinecap="square" strokeLinejoin="miter" strokeMiterlimit="10" strokeWidth={strokewidth}/>
      <path d="M19,31H2V11 c0-1.105,0.895-2,2-2h40c1.105,0,2,0.895,2,2v20H29" fill="none" stroke={fill} strokeLinecap="square" strokeLinejoin="miter" strokeMiterlimit="10" strokeWidth={strokewidth}/>
      <path d="M44,36v7 c0,1.105-0.895,2-2,2H6c-1.105,0-2-0.895-2-2v-7" fill="none" stroke={fill} strokeLinecap="square" strokeLinejoin="miter" strokeMiterlimit="10" strokeWidth={strokewidth}/>
      <rect height="8" width="10" fill="none" stroke={secondaryfill} strokeLinecap="square" strokeLinejoin="miter" strokeMiterlimit="10" strokeWidth={strokewidth} x="19" y="27"/>
    </g>
  </svg>
    );
  };


  export function Nodes(props) {
    const fill = props.fill || 'currentColor';
    const secondaryfill = props.secondaryfill || fill;
    const strokewidth = props.strokewidth || 1;
    const width = props.width || '1em';
    const height = props.height || '1em';

    return (
      <svg height={height} width={width} viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
    <g fill={fill}>
      <path d="M9,6.5c1.12,0,2.082-.675,2.511-1.638,1.438,.742,2.507,2.096,2.859,3.696,.077,.35,.388,.588,.731,.588,.054,0,.108-.005,.163-.018,.404-.089,.659-.49,.57-.894-.489-2.212-2.054-4.051-4.13-4.925-.213-1.306-1.34-2.309-2.705-2.309-1.517,0-2.75,1.233-2.75,2.75s1.233,2.75,2.75,2.75Z" fill={fill}/>
      <path d="M6.186,11.375c-.56-.969-1.626-1.466-2.674-1.355-.077-1.617,.561-3.219,1.769-4.324,.306-.279,.327-.754,.048-1.06-.28-.305-.754-.327-1.06-.047-1.672,1.529-2.482,3.804-2.201,6.038-.445,.362-.769,.847-.921,1.412-.189,.709-.092,1.451,.275,2.086,.367,.636,.96,1.092,1.67,1.282,.236,.063,.477,.095,.716,.095,.477,0,.946-.125,1.37-.37,1.312-.757,1.765-2.442,1.007-3.756Z" fill={fill}/>
      <path d="M16.853,12.039c-.19-.709-.646-1.303-1.281-1.67-1.312-.759-2.999-.306-3.757,1.007-.56,.97-.456,2.14,.164,2.992-1.36,.875-3.065,1.123-4.631,.629-.397-.124-.816,.095-.94,.489-.125,.395,.094,.816,.489,.941,.683,.216,1.388,.321,2.09,.321,1.525,0,3.032-.501,4.263-1.44,.305,.114,.62,.192,.943,.192,.239,0,.479-.031,.716-.095,.71-.19,1.303-.646,1.67-1.281s.465-1.377,.275-2.086Z" fill={secondaryfill}/>
    </g>
  </svg>
    );
  };


  export function Upload2(props) {
    const fill = props.fill || 'currentColor';
    const secondaryfill = props.secondaryfill || fill;
    const strokewidth = props.strokewidth || 1;
    const width = props.width || '1em';
    const height = props.height || '1em';

    return (
      <svg height={height} width={width} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <g fill={fill}>
      <path d="m18,9h-5v8h-2v-8h-5c-1.654,0-3,1.346-3,3v8c0,1.654,1.346,3,3,3h12c1.654,0,3-1.346,3-3v-8c0-1.654-1.346-3-3-3Z" fill={fill} strokeWidth="0"/>
      <polygon fill={secondaryfill} points="11 3.914 11 9 13 9 13 3.914 16 6.914 17.414 5.5 12 .086 6.586 5.5 8 6.914 11 3.914" strokeWidth="0"/>
    </g>
  </svg>
    );
  };


  export function Clipboard(props) {
    const fill = props.fill || 'currentColor';
    const secondaryfill = props.secondaryfill || fill;
    const strokewidth = props.strokewidth || 1;
    const width = props.width || '1em';
    const height = props.height || '1em';

    return (
      <svg height={height} width={width} viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
    <g fill={fill}>
      <path d="M12.75,2h-.275c-.123-.846-.845-1.5-1.725-1.5h-3.5c-.879,0-1.602,.654-1.725,1.5h-.275c-1.517,0-2.75,1.233-2.75,2.75V14.25c0,1.517,1.233,2.75,2.75,2.75h7.5c1.517,0,2.75-1.233,2.75-2.75V4.75c0-1.517-1.233-2.75-2.75-2.75Zm-5.75,.25c0-.138,.112-.25,.25-.25h3.5c.138,0,.25,.112,.25,.25v1c0,.138-.112,.25-.25,.25h-3.5c-.138,0-.25-.112-.25-.25v-1Z" fill={fill}/>
    </g>
  </svg>
    );
  };


  export function Cogwheel3(props) {
    const fill = props.fill || 'currentColor';
    const secondaryfill = props.secondaryfill || fill;
    const strokewidth = props.strokewidth || 1;
    const width = props.width || '1em';
    const height = props.height || '1em';

    return (
      <svg height={height} width={width} viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <g fill={fill}>
      <path d="M31.57,14.005l-3.846-.55a11.9,11.9,0,0,0-1.638-3.941L28.421,6.4a.5.5,0,0,0-.047-.653L26.253,3.625a.5.5,0,0,0-.653-.046L22.486,5.914a11.9,11.9,0,0,0-3.941-1.638L18,.429A.5.5,0,0,0,17.5,0h-3a.5.5,0,0,0-.495.429l-.55,3.847A11.9,11.9,0,0,0,9.514,5.914L6.4,3.579a.5.5,0,0,0-.653.046L3.626,5.747a.5.5,0,0,0-.047.653L5.914,9.514a11.9,11.9,0,0,0-1.638,3.941l-3.846.55A.5.5,0,0,0,0,14.5v3a.5.5,0,0,0,.43.5l3.846.55a11.9,11.9,0,0,0,1.638,3.941L3.579,25.6a.5.5,0,0,0,.047.653l2.121,2.122a.5.5,0,0,0,.354.146.494.494,0,0,0,.3-.1l3.114-2.335a11.923,11.923,0,0,0,3.941,1.638l.55,3.847A.5.5,0,0,0,14.5,32h3a.5.5,0,0,0,.5-.429l.55-3.847a11.923,11.923,0,0,0,3.941-1.638L25.6,28.421a.494.494,0,0,0,.3.1.5.5,0,0,0,.354-.146l2.121-2.122a.5.5,0,0,0,.047-.653l-2.335-3.114a11.9,11.9,0,0,0,1.638-3.941L31.57,18a.5.5,0,0,0,.43-.5v-3A.5.5,0,0,0,31.57,14.005ZM16,21a5,5,0,1,1,5-5A5,5,0,0,1,16,21Z" fill={fill}/>
    </g>
  </svg>
    );
  };
