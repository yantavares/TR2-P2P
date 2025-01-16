import { AxiosResponse } from "axios";
import { getActiveUsers } from "../../requests";
import { useEffect, useState } from "react";
import { User } from "../../types";

export const FileHandler = ({ userId }: { userId: number }) => {
  const [response, setResponse] = useState<AxiosResponse | null>(null);
  const [resources, setResources] = useState<string[]>([]);
  const [onlineUsers, setOnlineUsers] = useState<number>(0);

  const handleGetActiveUsers = async () => {
    const response = await getActiveUsers();
    setResponse(response);
  };

  useEffect(() => {
    if (!response) return;

    const activeUsers: {
      [key: string]: User;
    } = response?.data?.active_users;
    console.log("Active Users:", activeUsers);

    if (activeUsers && typeof activeUsers === "object") {
      const resources: string[] = [];
      let onlineCount = 0;

      Object.values(activeUsers).forEach((user: User) => {
        if (user.resources) {
          resources.push(...user.resources);
        }
        onlineCount++;
      });

      console.log("All Resources:", resources);
      console.log("Online Users:", onlineCount);

      setResources(resources);
      setOnlineUsers(onlineCount);
    }
  }, [response]);

  return (
    <div
      style={{
        width: "50%",
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
      }}
    >
      <h2>FileHandler - {userId}</h2>
      <p style={{ margin: 0, padding: 0 }}>
        {onlineUsers == 2
          ? onlineUsers + " online user"
          : onlineUsers + " online users"}
      </p>
      <div
        style={{
          backgroundColor: "lightgray",
          height: "20rem",
          borderRadius: "1rem",
        }}
      >
        <h3>Resources</h3>
        <ul>
          {resources.map((resource, index) => (
            <p style={{ color: "black" }} key={index}>
              {resource}
            </p>
          ))}
        </ul>
      </div>
      <div>
        <button onClick={() => handleGetActiveUsers()}>Refresh</button>
      </div>
    </div>
  );
};

export default FileHandler;
