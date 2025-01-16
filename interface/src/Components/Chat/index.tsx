export const Chat = ({ userId }: { userId: number }) => {
  return (
    <div style={{ width: "50%" }}>
      <h2>Chat - {userId}</h2>
      <div
        style={{
          backgroundColor: "lightgray",
          height: "20rem",
          borderRadius: "1rem",
        }}
      ></div>
    </div>
  );
};

export default Chat;
