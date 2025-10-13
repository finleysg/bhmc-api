import os
import time
import requests
import structlog
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

logger = structlog.get_logger(__name__)


class GolfGeniusAPIError(Exception):
    """Base exception for Golf Genius API errors"""

    pass


class GolfGeniusAuthError(GolfGeniusAPIError):
    """Authentication related errors"""

    pass


class GolfGeniusRateLimitError(GolfGeniusAPIError):
    """Rate limit exceeded errors"""

    pass


class GolfGeniusAPIClient:
    """
    Golf Genius API client for handling authentication and requests
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://www.golfgenius.com",
    ):
        self.api_key = api_key or os.getenv("GOLF_GENIUS_API_KEY")
        self.base_url = base_url
        self.session = requests.Session()

        if not self.api_key:
            raise GolfGeniusAuthError("Golf Genius API key not provided")

        # Set default timeout
        self.timeout = 30

        # Rate limit retry configuration
        self.max_retries = 3
        self.retry_delay_base = 1  # Base delay in seconds
        self.retry_delay_max = 60  # Maximum delay in seconds

        logger.info(
            "Golf Genius API client initialized",
            base_url=self.base_url,
            max_retries=self.max_retries,
        )

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Golf Genius API with retry logic for rate limiting

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            data: Form data
            json_data: JSON data for POST/PUT

        Returns:
            Response data as dictionary

        Raises:
            GolfGeniusAPIError: For API errors
            GolfGeniusAuthError: For authentication errors
            GolfGeniusRateLimitError: For rate limit errors after max retries
        """
        url = urljoin(self.base_url, endpoint)

        # Add API key to endpoint path
        if "{api_key}" in endpoint:
            endpoint = endpoint.format(api_key=self.api_key)
            url = urljoin(self.base_url, endpoint)

        # Log out the url
        logger.info("Making request", method=method, url=url, params=params)

        headers = {"Accept": "application/json", "User-Agent": "BHMC-Integration/1.0"}

        if json_data:
            headers["Content-Type"] = "application/json"
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    "Making Golf Genius API request",
                    method=method,
                    url=url,
                    params=params,
                    attempt=attempt + 1,
                )

                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json_data,
                    headers=headers,
                    timeout=self.timeout,
                )

                logger.debug(
                    "Golf Genius API response",
                    status_code=response.status_code,
                    response_size=len(response.content),
                    attempt=attempt + 1,
                )

                # Handle rate limiting with retry
                if response.status_code == 429:
                    if attempt < self.max_retries:
                        # Calculate exponential backoff delay
                        delay = min(
                            self.retry_delay_base * (2**attempt), self.retry_delay_max
                        )

                        # Check for Retry-After header
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                # Use the Retry-After value if it's reasonable
                                retry_delay = min(
                                    int(retry_after), self.retry_delay_max
                                )
                                delay = max(delay, retry_delay)
                            except (ValueError, TypeError):
                                pass

                        logger.warning(
                            "Rate limit exceeded, retrying",
                            attempt=attempt + 1,
                            max_retries=self.max_retries,
                            delay=delay,
                            retry_after=retry_after,
                        )

                        time.sleep(delay)
                        continue
                    else:
                        logger.error(
                            "Rate limit exceeded, max retries reached",
                            attempts=attempt + 1,
                        )
                        raise GolfGeniusRateLimitError(
                            "Rate limit exceeded after maximum retries"
                        )

                # Handle authentication errors (don't retry)
                if response.status_code == 401:
                    raise GolfGeniusAuthError(
                        "Invalid API key or authentication failed"
                    )

                # Handle other client/server errors (don't retry)
                if response.status_code >= 400:
                    error_msg = f"API request failed with status {response.status_code}"
                    try:
                        error_data = response.json()
                        if "errors" in error_data:
                            error_msg += f": {error_data['errors']}"
                    except:
                        error_msg += f": {response.text}"

                    raise GolfGeniusAPIError(error_msg)

                # Success - return JSON response
                return response.json()

            except (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.RequestException,
            ) as e:
                last_exception = e

                if attempt < self.max_retries:
                    # Retry on network errors with exponential backoff
                    delay = min(
                        self.retry_delay_base * (2**attempt), self.retry_delay_max
                    )

                    logger.warning(
                        "Network error, retrying",
                        error=str(e),
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        delay=delay,
                    )

                    time.sleep(delay)
                    continue
                else:
                    logger.error(
                        "Network error, max retries reached",
                        error=str(e),
                        attempts=attempt + 1,
                    )
                    break

        # If we get here, we've exhausted all retries
        if last_exception:
            if isinstance(last_exception, requests.exceptions.Timeout):
                raise GolfGeniusAPIError("Request timeout after retries")
            elif isinstance(last_exception, requests.exceptions.ConnectionError):
                raise GolfGeniusAPIError("Connection error after retries")
            else:
                raise GolfGeniusAPIError(
                    f"Request failed after retries: {str(last_exception)}"
                )

        # Fallback error
        raise GolfGeniusAPIError("Request failed after maximum retries")

    def get_master_roster(
        self, page: Optional[int] = None, photo: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get master roster from Golf Genius

        Args:
            page: Page number for pagination
            photo: Include profile pictures

        Returns:
            List of member dictionaries
        """
        params = {}
        if page is not None:
            params["page"] = page
        if photo:
            params["photo"] = "true"

        endpoint = f"/api_v2/{self.api_key}/master_roster"
        response = self._make_request("GET", endpoint, params=params)

        logger.info(
            "Retrieved master roster",
            member_count=len(response) if isinstance(response, list) else 0,
            page=page,
        )

        return response if isinstance(response, list) else []

    def get_tournament_results(
        self, event_id: str, round_id: str, tournament_id: str
    ) -> Dict[str, Any]:
        """
        Get tournament results from Golf Genius

        Args:
            event_id: Golf Genius event ID
            round_id: Golf Genius round ID
            tournament_id: Golf Genius tournament ID

        Returns:
            Tournament results data
        """
        endpoint = f"/api_v2/{self.api_key}/events/{event_id}/rounds/{round_id}/tournaments/{tournament_id}.json"
        response = self._make_request("GET", endpoint)

        logger.info(
            "Retrieved tournament results",
            event_id=event_id,
            round_id=round_id,
            tournament_id=tournament_id,
        )

        return response if isinstance(response, dict) else {}

    def get_master_roster_member(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get specific member from master roster by email

        Args:
            email: Member's email address

        Returns:
            Member dictionary if found, None otherwise
        """
        endpoint = f"/api_v2/{self.api_key}/master_roster_member/{email}"

        try:
            response = self._make_request("GET", endpoint)

            if "member" in response:
                logger.info("Found member in master roster", email=email)
                return response["member"]

            return None

        except GolfGeniusAPIError as e:
            if "404" in str(e):
                logger.info("Member not found in master roster", email=email)
                return None
            raise

    def get_seasons(self) -> List[Dict[str, Any]]:
        """
        Get all seasons from Golf Genius

        Returns:
            List of season dictionaries
        """
        endpoint = f"/api_v2/{self.api_key}/seasons"
        response = self._make_request("GET", endpoint)

        logger.info(
            "Retrieved seasons",
            season_count=len(response) if isinstance(response, list) else 0,
        )

        return response if isinstance(response, list) else []

    def get_events(
        self,
        season_id: str,
        category_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get events from Golf Genius

        Args:
            season_id: Filter by season ID
            category_id: Filter by category ID

        Returns:
            List of event dictionaries
        """
        params = {}
        if season_id:
            params["season"] = season_id
        if category_id:
            params["category"] = category_id

        endpoint = f"/api_v2/{self.api_key}/events"
        response = self._make_request("GET", endpoint, params=params)

        logger.info(
            "Retrieved events",
            event_count=len(response) if isinstance(response, list) else 0,
        )

        return response if isinstance(response, list) else []

    def get_event_rounds(self, event_id: str) -> List[Dict[str, Any]]:
        """
        Get rounds for a specific event from Golf Genius

        Args:
            event_id: Golf Genius event ID

        Returns:
            List of round dictionaries
        """
        endpoint = f"/api_v2/{self.api_key}/events/{event_id}/rounds"
        response = self._make_request("GET", endpoint)

        logger.info(
            "Retrieved event rounds",
            event_id=event_id,
            round_count=len(response) if isinstance(response, list) else 0,
        )

        return response if isinstance(response, list) else []

    def get_round_tournaments(
        self, event_id: str, round_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get tournaments for a specific round from Golf Genius

        Args:
            event_id: Golf Genius event ID
            round_id: Golf Genius round ID

        Returns:
            List of tournament dictionaries
        """
        endpoint = (
            f"/api_v2/{self.api_key}/events/{event_id}/rounds/{round_id}/tournaments"
        )
        response = self._make_request("GET", endpoint)

        logger.info(
            "Retrieved round tournaments",
            event_id=event_id,
            round_id=round_id,
            tournament_count=len(response) if isinstance(response, list) else 0,
        )

        return response if isinstance(response, list) else []

    def get_event_courses(self, event_id: str) -> List[Dict[str, Any]]:
        """
        Get courses for a specific event from Golf Genius

        Args:
            event_id: Golf Genius event ID

        Returns:
            List of course dictionaries
        """
        endpoint = f"/api_v2/{self.api_key}/events/{event_id}/courses"
        response = self._make_request("GET", endpoint)

        # Extract courses from the response format
        courses = []
        if isinstance(response, dict) and "courses" in response:
            courses = response["courses"]
        elif isinstance(response, list):
            courses = response

        logger.info(
            "Retrieved event courses", event_id=event_id, course_count=len(courses)
        )

        return courses

    def get_event_roster(
        self, event_id: str, photo: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get the full event roster from Golf Genius, handling pagination.

        Args:
            event_id: Golf Genius event ID
            photo: Include profile pictures

        Returns:
            List of member dictionaries (flattened)
        """
        members: List[Dict[str, Any]] = []
        page = 1

        while True:
            params = {"page": page}
            if photo:
                params["photo"] = "true"

            endpoint = f"/api_v2/{self.api_key}/events/{event_id}/roster"
            try:
                response = self._make_request("GET", endpoint, params=params)
            except GolfGeniusAPIError:
                # Bubble up error to caller
                raise

            # Response may be a list of {"member": {...}} or a list of member dicts
            if not response:
                break

            if isinstance(response, list):
                for item in response:
                    if isinstance(item, dict) and "member" in item:
                        members.append(item["member"])
                    else:
                        members.append(item)
            else:
                break

            # If less than page size (100) then we are done; otherwise increment page
            if len(response) < 100:
                break

            page += 1

        logger.info(
            "Retrieved event roster", event_id=event_id, member_count=len(members)
        )
        return members

    def create_member_registration(
        self, event_id: str, member_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a member registration for an event in Golf Genius

        Args:
            event_id: Golf Genius event ID
            member_data: Member registration data

        Returns:
            API response data
        """
        endpoint = f"/api_v2/events/{event_id}/members"
        response = self._make_request("POST", endpoint, json_data=member_data)

        logger.info(
            "Created member registration",
            event_id=event_id,
            external_id=member_data.get("external_id"),
            email=member_data.get("email"),
        )

        return response

    def update_member_registration(
        self, event_id: str, member_id: str, member_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing member registration for an event in Golf Genius.

        Args:
            event_id: Golf Genius event ID
            member_id: Golf Genius member ID
            member_data: Member registration data to update

        Returns:
            API response data
        """
        endpoint = f"/api_v2/events/{event_id}/members/{member_id}"
        response = self._make_request("PUT", endpoint, json_data=member_data)

        logger.info(
            "Updated member registration",
            event_id=event_id,
            member_id=member_id,
            external_id=member_data.get("external_id"),
            email=member_data.get("email"),
        )

        return response

    def get_round_tee_sheet(
        self, event_id: str, round_id: str, include_all_custom_fields: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get round tee sheet and scores from Golf Genius

        Args:
            event_id: Golf Genius event ID
            round_id: Golf Genius round ID
            include_all_custom_fields: Include all custom fields

        Returns:
            List of pairing group dictionaries with player scores
        """
        params = {}
        if include_all_custom_fields:
            params["include_all_custom_fields"] = "true"

        endpoint = f"/api_v2/{self.api_key}/events/{event_id}/rounds/{round_id}/tee_sheet"
        response = self._make_request("GET", endpoint, params=params)

        logger.info(
            "Retrieved round tee sheet",
            event_id=event_id,
            round_id=round_id,
            pairing_count=len(response) if isinstance(response, list) else 0,
        )

        return response if isinstance(response, list) else []
