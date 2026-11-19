// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Publica una huella sin almacenar reseñas ni datos personales.
contract Anchor {
    mapping(bytes32 => uint64) public anchoredAt;

    event Anchored(bytes32 indexed hash, address indexed submitter, uint64 timestamp);

    /// @dev La operación es idempotente para permitir reintentos tras timeouts.
    function anchor(bytes32 hash) external {
        require(hash != bytes32(0), "Anchor: zero hash");
        if (anchoredAt[hash] != 0) {
            return;
        }

        uint64 timestamp = uint64(block.timestamp);
        anchoredAt[hash] = timestamp;
        emit Anchored(hash, msg.sender, timestamp);
    }
}
