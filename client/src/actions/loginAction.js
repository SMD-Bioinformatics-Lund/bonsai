import { FETCH_USER } from "../actions/types";
import { getUser } from "../api";

export const fetchUser = (userNmae) => dispatch => {
  getUser(userNmae)
  .then(user => dispatch({
    type: FETCH_USER, 
    payload: user
  }))
}