// airtable.js

import { useState, useEffect } from "react";
import { Box, Button, CircularProgress } from "@mui/material";
import axios from "axios";
import React from "react";

export const HubspotIntegration = ({
  user,
  org,
  integrationParams,
  setIntegrationParams,
}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);

  // Function to open OAuth in a new window
  const handleConnectClick = async () => {
    try {
      setIsConnecting(true);
      const formData = new FormData();
      formData.append("user_id", user);
      formData.append("org_id", org);
      const response = await axios.post(
        `http://localhost:8000/integrations/hubspot/authorize`,
        formData
      );
      const authURL = response?.data;

      const newWindow = window.open(
        authURL,
        "Hubspot Authorization",
        "width=600, height=600"
      );

      // Polling for the window to close
      const pollTimer = window.setInterval(() => {
        if (newWindow?.closed !== false) {
          window.clearInterval(pollTimer);
          handleWindowClosed();
        }
      }, 200);
    } catch (e) {
      console.error(e);
      setIsConnecting(false);
      alert(e?.response?.data?.detail);
    }
  };

  // Function to handle logic when the OAuth window closes
  const handleWindowClosed = async () => {
    console.log("Handling window close.");
    try {
      const formData = new FormData();
      formData.append("user_id", user);
      formData.append("org_id", org);
      const response = await axios.post(
        `http://localhost:8000/integrations/hubspot/credentials`,
        formData
      );
      const credentials = response.data;
      if (credentials) {
        setIsConnecting(false);
        setIsConnected(true);
        setIntegrationParams((prev) => ({
          ...prev,
          credentials: credentials,
          type: "Hubspot",
        }));
      }
      setIsConnecting(false);
    } catch (e) {
      setIsConnecting(false);
      alert(e?.response?.data?.detail);
    }
  };

  useEffect(() => {
    setIsConnected(integrationParams?.credentials ? true : false);
  }, []);

  return (
    <>
      <Box sx={{ mt: 2 }}>
        Parameters
        <Box
          display="flex"
          alignItems="center"
          justifyContent="center"
          sx={{ mt: 2 }}
        >
          <Button
            variant="contained"
            onClick={isConnected ? () => {} : handleConnectClick}
            color={isConnected ? "success" : "primary"}
            disabled={isConnecting}
            style={{
              pointerEvents: isConnected ? "none" : "auto",
              cursor: isConnected ? "default" : "pointer",
              opacity: isConnected ? 1 : undefined,
            }}
          >
            {isConnected ? (
              "Hubspot Connected"
            ) : isConnecting ? (
              <CircularProgress size={20} />
            ) : (
              "Connect to Hubspot"
            )}
          </Button>
        </Box>
      </Box>
    </>
  );
};

const cardStyle = {
  border: "1px solid #ddd",
  borderRadius: "12px",
  padding: "16px",
  margin: "12px",
  backgroundColor: "#f9f9f9",
  boxShadow: "0 2px 6px rgba(0, 0, 0, 0.1)",
  maxWidth: "400px",
};

const labelStyle = {
  fontWeight: "bold",
  marginRight: "6px",
  color: "#333",
};

const valueStyle = {
  color: "#555",
};

const itemTypeColors = {
  contacts: "#2E86C1",
  companies: "#27AE60",
  deals: "#AF7AC5",
  tickets: "#E67E22",
};

const getTitleColor = (type) => itemTypeColors[type] || "#34495E";

const HubspotItemCard = ({ item }) => {
  return (
    <div style={cardStyle}>
      <h3 style={{ color: getTitleColor(item.type), marginBottom: "10px" }}>
        {item.name || "Unnamed Item"}
      </h3>
      <div>
        <span style={labelStyle}>Type:</span>
        <span style={valueStyle}>{item.type}</span>
      </div>
      <div>
        <span style={labelStyle}>ID:</span>
        <span style={valueStyle}>{item.id}</span>
      </div>
      {item.creation_time && (
        <div>
          <span style={labelStyle}>Created:</span>
          <span style={valueStyle}>
            {new Date(item.creation_time).toLocaleString()}
          </span>
        </div>
      )}
      {item.last_modified_time && (
        <div>
          <span style={labelStyle}>Updated:</span>
          <span style={valueStyle}>
            {new Date(item.last_modified_time).toLocaleString()}
          </span>
        </div>
      )}
    </div>
  );
};

export const HubspotItems = ({ items }) => {
  if (!items || items.length === 0) {
    return <p>No HubSpot items to display.</p>;
  }

  return (
    <div
      style={{ display: "flex", flexWrap: "wrap", justifyContent: "center" }}
    >
      {items.map((item) => (
        <HubspotItemCard key={item.id} item={item} />
      ))}
    </div>
  );
};
