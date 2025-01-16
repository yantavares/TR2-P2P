import { useNavigate } from "react-router-dom";
import Chat from "../../Components/Chat";
import FileHandler from "../../Components/FileHandler";
import { sendKeepAlive } from "../../requests";

const Room = () => {
  const navigate = useNavigate();
  const urlParams = new URLSearchParams(window.location.search);
  const userId = urlParams.get("user_id");

  if (!userId) {
    console.error("User ID not found in query params.");
    navigate("/");
    return null;
  }

  setTimeout(() => {
    sendKeepAlive(userId);
  }, 5000);

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        padding: "5%",
        width: "100%",
      }}
    >
      <div
        style={{
          backgroundColor: "gray",
          padding: "2rem",
          borderRadius: "1rem",
          height: "30rem",
          width: "100%",
          display: "flex",
          gap: "2rem",
          justifyContent: "space-around",
        }}
      >
        <Chat userId={userId} />
        <FileHandler userId={userId} />
      </div>
    </div>
  );
};
export default Room;
