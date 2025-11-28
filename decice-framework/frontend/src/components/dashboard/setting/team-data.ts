import {isEqual, uniqWith} from "lodash";

const columns = [
  {name: "NAME", uid: "name", sortable: true},
  {name: "ROLE", uid: "role", sortable: true},
  {name: "STATUS", uid: "status", sortable: true},
  {name: "ACTIONS", uid: "actions"},
];

const users = [
  {
    id: 1,
    name: "Özay Tokgöz",
    role: "Backend",
    team: "Venit",
    status: "active",
    age: "27",
    avatar: "https://venit.org/venit-website/venit_website/media/members/%C3%B6zay.jpg",
    email: "ozay.tokgoz@venit.org",
  },
  {
    id: 2,
    name: "Berkay Yaman",
    role: "V2X",
    team: "Venit",
    status: "pending",
    age: "30",
    avatar: "https://venit.org/venit-website/venit_website/media/members/berkay.jpeg",
    email: "berkay.yaman@venit.org",
  },
];

/**
 * To use this function you need to install lodash in your project
 * ```bash
 * npm install lodash
 * ```
 */
const rolesOptions = uniqWith(
  users.map((user) => {
    return {
      name: user.role,
      uid: user.role.toLowerCase(),
    };
  }),
  isEqual,
);

/**
 * To use this function you need to install lodash in your project
 * ```bash
 * npm install lodash
 * ```
 */
const statusOptions = uniqWith(
  users.map((user) => {
    return {
      name: user.status,
      uid: user.status.toLowerCase(),
    };
  }),
  isEqual,
);

export {columns, users, rolesOptions, statusOptions};
