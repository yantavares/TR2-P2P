import axios, { AxiosResponse } from "axios";

const TRACKER_URL = "http://localhost:5000";

interface RegisterResponse {
  message: string;
}

export async function registerUser(
  userId: string,
  resources: string[]
): Promise<AxiosResponse<RegisterResponse>> {
  return axios.post<RegisterResponse>(`${TRACKER_URL}/register`, {
    user_id: userId,
    resources,
  });
}

export async function sendKeepAlive(userId: string) {
  const response = await axios.post(`${TRACKER_URL}/keep_alive`, {
    user_id: userId,
  });
  console.log(response.data);
}

export async function getActiveUsers(): Promise<AxiosResponse<string[]>> {
  const response = await axios.get(`${TRACKER_URL}/active_users`);
  console.log(response.data);
  return response;
}
