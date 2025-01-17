import { faDownload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

const File = ({ name }: { name: string }) => {
  return (
    <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
      <p style={{ color: "black", fontWeight: "bold" }}>{name}</p>
      <p style={{ color: "black" }}>{10} bytes</p>
      <p style={{ color: "black" }}>{"txt file"}</p>
      <FontAwesomeIcon
        style={{ color: "green", cursor: "pointer" }}
        icon={faDownload}
      />
    </div>
  );
};
export default File;
