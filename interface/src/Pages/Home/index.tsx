import { useNavigate } from "react-router-dom";
import { registerUser } from "../../requests";
import { User } from "../../types";

const mockUsers = [
  {
    id: "user1",
    resources: ["file1", "file2"],
  },
  {
    id: "user2",
    resources: ["file3", "file4"],
  },
  {
    id: "user3",
    resources: ["file3", "file1"],
  },
];

const Home = () => {
  const navigate = useNavigate();
  const handleConnect = async (user: User) => {
    try {
      const response = await registerUser(user.id, user.resources);
      if (
        response.status === 200 &&
        response.data.message === "Registered successfully"
      ) {
        navigate("/room?user_id=" + user.id);
      } else {
        console.error("Registration failed:", response.data);
      }
    } catch (error) {
      console.error("Error connecting to the server:", error);
    }
  };

  return (
    <>
      <div>
        <h2>Welcome to our P2P network.</h2>
        <p>
          This is a simple P2P network that allows you to connect to other
          peeers, chat and send files.
        </p>
        <div>
          <button onClick={() => handleConnect(mockUsers[0])}>Connect!</button>
        </div>
        <p>Made for the TR2 course at the University of Brasília.</p>
      </div>
    </>
  );
};
export default Home;
