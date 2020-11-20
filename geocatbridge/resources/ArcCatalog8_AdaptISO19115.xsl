<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:output method="xml" encoding="UTF-8" omit-xml-declaration="no" version="1.0" indent="yes" />
	<!--<xsl:output method="xml" doctype-system="ISO_19115.dtd"/>-->

  <xsl:template match="/">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>
        
	<xsl:template match="DateTypCd">
		<DateTypCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>creation</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>publication</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>revision</xsl:text></xsl:attribute>
			</xsl:if>
		</DateTypCd>
	</xsl:template>
	<xsl:template match="orDesc">
		<orDesc>
			<xsl:choose>
				<xsl:when test=".=001">
					<xsl:text>Live Data and Maps</xsl:text>
				</xsl:when>
				<xsl:when test=".=002">
					<xsl:text>Downloadable data</xsl:text>
				</xsl:when>
				<xsl:when test=".=003">
					<xsl:text>Offline Data</xsl:text>
				</xsl:when>
				<xsl:when test=".=004">
					<xsl:text>Static Map Images</xsl:text>
				</xsl:when>
				<xsl:when test=".=005">
					<xsl:text>Other Documents</xsl:text>
				</xsl:when>
				<xsl:when test=".=006">
					<xsl:text>Applications</xsl:text>
				</xsl:when>
				<xsl:when test=".=007">
					<xsl:text>Geographic Services</xsl:text>
				</xsl:when>
				<xsl:when test=".=008">
					<xsl:text>Clearinghouses</xsl:text>
				</xsl:when>
				<xsl:when test=".=009">
					<xsl:text>Map Files</xsl:text>
				</xsl:when>
				<xsl:when test=".=010">
					<xsl:text>Geographic Activities</xsl:text>
				</xsl:when>
				<xsl:otherwise><xsl:value-of select="." /></xsl:otherwise>
			</xsl:choose>			
		</orDesc>
	</xsl:template>
	<xsl:template match="OnFunctCd">
		<OnFunctCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>download</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>information</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>offlineAccess</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>order</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>search</xsl:text></xsl:attribute>
			</xsl:if>
		</OnFunctCd>
	</xsl:template>
	<xsl:template match="PresFormCd">
		<PresFormCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>documentDigital</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>documentHardcopy</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>imageDigital</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>imageHardcopy</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>mapDigital</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>mapHardcopy</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=007">
				<xsl:attribute name="value"><xsl:text>modelDigital</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=008">
				<xsl:attribute name="value"><xsl:text>modelHardcopy</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=009">
				<xsl:attribute name="value"><xsl:text>profileDigital</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=010">
				<xsl:attribute name="value"><xsl:text>profileHardcopy</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=011">
				<xsl:attribute name="value"><xsl:text>tableDigital</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=012">
				<xsl:attribute name="value"><xsl:text>tableHardcopy</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=013">
				<xsl:attribute name="value"><xsl:text>videoDigital</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=014">
				<xsl:attribute name="value"><xsl:text>videoHardcopy</xsl:text></xsl:attribute>
			</xsl:if>
		</PresFormCd>
	</xsl:template>
	<xsl:template match="RoleCd">
		<RoleCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>resourceProvider</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>custodian</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>owner</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>user</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>distributor</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>originator</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=007">
				<xsl:attribute name="value"><xsl:text>pointOfContact</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=008">
				<xsl:attribute name="value"><xsl:text>principalInvestigator</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=009">
				<xsl:attribute name="value"><xsl:text>processor</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=010">
				<xsl:attribute name="value"><xsl:text>publisher</xsl:text></xsl:attribute>
			</xsl:if>
		</RoleCd>
	</xsl:template>
	<xsl:template match="EvalMethTypeCd">
		<EvalMethTypeCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>directInternal</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>directExternal</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>indirect</xsl:text></xsl:attribute>
			</xsl:if>
		</EvalMethTypeCd>
	</xsl:template>
	<xsl:template match="AscTypeCd">
		<AscTypeCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>crossReference</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>largerWorkCitation</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>partOfSeamlessDatabase</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>source</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>stereomate</xsl:text></xsl:attribute>
			</xsl:if>
		</AscTypeCd>
	</xsl:template>
	<xsl:template match="InitTypCd">
		<InitTypCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>campaign</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>collection</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>exercise</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>experiment</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>investigation</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>mission</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=007">
				<xsl:attribute name="value"><xsl:text>nonImageSensor</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=008">
				<xsl:attribute name="value"><xsl:text>operation</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=009">
				<xsl:attribute name="value"><xsl:text>platform</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=010">
				<xsl:attribute name="value"><xsl:text>process</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=011">
				<xsl:attribute name="value"><xsl:text>program</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=012">
				<xsl:attribute name="value"><xsl:text>project</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=013">
				<xsl:attribute name="value"><xsl:text>study</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=014">
				<xsl:attribute name="value"><xsl:text>task</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=015">
				<xsl:attribute name="value"><xsl:text>trial</xsl:text></xsl:attribute>
			</xsl:if>
		</InitTypCd>
	</xsl:template>
	<xsl:template match="CellGeoCd">
		<CellGeoCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>point</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>area</xsl:text></xsl:attribute>
			</xsl:if>
		</CellGeoCd>
	</xsl:template>
	<xsl:template match="CharSetCd">
		<CharSetCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>ucs2</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>ucs4</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>utf7</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>utf8</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>utf16</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>8859part1</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=007">
				<xsl:attribute name="value"><xsl:text>8859part2</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=008">
				<xsl:attribute name="value"><xsl:text>8859part3</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=009">
				<xsl:attribute name="value"><xsl:text>8859part4</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=010">
				<xsl:attribute name="value"><xsl:text>8859part5</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=011">
				<xsl:attribute name="value"><xsl:text>8859part6</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=012">
				<xsl:attribute name="value"><xsl:text>8859part7</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=013">
				<xsl:attribute name="value"><xsl:text>8859part8</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=014">
				<xsl:attribute name="value"><xsl:text>8859part9</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=015">
				<xsl:attribute name="value"><xsl:text>8859part11</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=016">
				<xsl:attribute name="value"><xsl:text>8859part14</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=017">
				<xsl:attribute name="value"><xsl:text>8859part15</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=018">
				<xsl:attribute name="value"><xsl:text>jis</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=019">
				<xsl:attribute name="value"><xsl:text>shiftJIS</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=020">
				<xsl:attribute name="value"><xsl:text>eucJP</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=021">
				<xsl:attribute name="value"><xsl:text>usAscii</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=022">
				<xsl:attribute name="value"><xsl:text>ebcdic</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=023">
				<xsl:attribute name="value"><xsl:text>eucKR</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=024">
				<xsl:attribute name="value"><xsl:text>big5</xsl:text></xsl:attribute>
			</xsl:if>
		</CharSetCd>
	</xsl:template>
	<xsl:template match="ClasscationCd">
		<ClasscationCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>unclassified</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>restricted</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>confidential</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>secret</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>topsecret</xsl:text></xsl:attribute>
			</xsl:if>
		</ClasscationCd>
	</xsl:template>
	<xsl:template match="ContentTypCd">
		<ContentTypCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>image</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>thematicClassification</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>physicalMeasurement</xsl:text></xsl:attribute>
			</xsl:if>
		</ContentTypCd>
	</xsl:template>
	<xsl:template match="DatatypeCd">
		<DatatypeCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>class</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>codelist</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>enumeration</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>codelistElement</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>abstractClass</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>aggregateClass</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=007">
				<xsl:attribute name="value"><xsl:text>specifiedClass</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=008">
				<xsl:attribute name="value"><xsl:text>datatypeClass</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=009">
				<xsl:attribute name="value"><xsl:text>interfaceClass</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=010">
				<xsl:attribute name="value"><xsl:text>unionClass</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=011">
				<xsl:attribute name="value"><xsl:text>metaclass</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=012">
				<xsl:attribute name="value"><xsl:text>typeClass</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=013">
				<xsl:attribute name="value"><xsl:text>characterString</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=014">
				<xsl:attribute name="value"><xsl:text>integer</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=015">
				<xsl:attribute name="value"><xsl:text>association</xsl:text></xsl:attribute>
			</xsl:if>
		</DatatypeCd>
	</xsl:template>
	<xsl:template match="DimNameTypCd">
		<DimNameTypCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>row</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>column</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>vertical</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>track</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>crossTrack</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>line</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=007">
				<xsl:attribute name="value"><xsl:text>sample</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=008">
				<xsl:attribute name="value"><xsl:text>time</xsl:text></xsl:attribute>
			</xsl:if>
		</DimNameTypCd>
	</xsl:template>
	<xsl:template match="GeoObjTypCd">
		<GeoObjTypCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>complexes</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>composites</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>curve</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>point</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>solid</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>surface</xsl:text></xsl:attribute>
			</xsl:if>
		</GeoObjTypCd>
	</xsl:template>
	<xsl:template match="ImgCondCd">
		<ImgCondCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>blurredImage</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>cloud</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>degradingObliquity</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>fog</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>heavySmokeOrDust</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>night</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=007">
				<xsl:attribute name="value"><xsl:text>rain</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=008">
				<xsl:attribute name="value"><xsl:text>semiDarkness</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=009">
				<xsl:attribute name="value"><xsl:text>shadow</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=010">
				<xsl:attribute name="value"><xsl:text>snow</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=011">
				<xsl:attribute name="value"><xsl:text>terrainMasking</xsl:text></xsl:attribute>
			</xsl:if>
		</ImgCondCd>
	</xsl:template>
	<xsl:template match="KeyTypCd">
		<KeyTypCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>discipline</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>place</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>stratum</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>temporal</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>theme</xsl:text></xsl:attribute>
			</xsl:if>
		</KeyTypCd>
	</xsl:template>
	<xsl:template match="MaintFreqCd">
		<MaintFreqCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>continual</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>daily</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>weekly</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>fortnightly</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>monthly</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>quarterly</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=007">
				<xsl:attribute name="value"><xsl:text>biannually</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=008">
				<xsl:attribute name="value"><xsl:text>annually</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=009">
				<xsl:attribute name="value"><xsl:text>asNeeded</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=010">
				<xsl:attribute name="value"><xsl:text>irregular</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=011">
				<xsl:attribute name="value"><xsl:text>notPlanned</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=998">
				<xsl:attribute name="value"><xsl:text>unknown</xsl:text></xsl:attribute>
			</xsl:if>
		</MaintFreqCd>
	</xsl:template>
	<xsl:template match="MedFormCd">
		<MedFormCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>cpio</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>tar</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>highSierra</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>iso9660</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>iso9660RockRidge</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>iso9660AppleHFS</xsl:text></xsl:attribute>
			</xsl:if>
		</MedFormCd>
	</xsl:template>
	<xsl:template match="MedNameCd">
		<MedNameCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>cdRom</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>dvd</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>dvdRom</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>3halfInchFloppy</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>5quarterInchFloppy</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>7trackTape</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=007">
				<xsl:attribute name="value"><xsl:text>9trackTape</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=008">
				<xsl:attribute name="value"><xsl:text>3480Cartridge</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=009">
				<xsl:attribute name="value"><xsl:text>3490Cartridge</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=010">
				<xsl:attribute name="value"><xsl:text>3580Cartridge</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=011">
				<xsl:attribute name="value"><xsl:text>4mmCartridgeTape</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=012">
				<xsl:attribute name="value"><xsl:text>8mmCartridgeTape</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=013">
				<xsl:attribute name="value"><xsl:text>1quarterInchCartridgeTape</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=014">
				<xsl:attribute name="value"><xsl:text>digitalLinearTape</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=015">
				<xsl:attribute name="value"><xsl:text>onLine</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=016">
				<xsl:attribute name="value"><xsl:text>satellite</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=017">
				<xsl:attribute name="value"><xsl:text>telephoneLink</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=018">
				<xsl:attribute name="value"><xsl:text>hardcopy</xsl:text></xsl:attribute>
			</xsl:if>
		</MedNameCd>
	</xsl:template>
	<xsl:template match="ObCd">
		<ObCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>mandatory</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>optional</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>conditional</xsl:text></xsl:attribute>
			</xsl:if>
		</ObCd>
	</xsl:template>
	<xsl:template match="PixOrientCd">
		<PixOrientCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>center</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>lowerLeft</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>lowerRight</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>upperRight</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>upperLeft</xsl:text></xsl:attribute>
			</xsl:if>
		</PixOrientCd>
	</xsl:template>
	<xsl:template match="ProgCd">
		<ProgCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>completed</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>historicalArchive</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>obsolete</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>onGoing</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>planned</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>required</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=007">
				<xsl:attribute name="value"><xsl:text>underdevelopment</xsl:text></xsl:attribute>
			</xsl:if>
		</ProgCd>
	</xsl:template>
	<xsl:template match="RestrictCd">
		<RestrictCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>copyright</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>patent</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>patentPending</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>trademark</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>license</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>intellectualPropertyRights</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=007">
				<xsl:attribute name="value"><xsl:text>restricted</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=008">
				<xsl:attribute name="value"><xsl:text>otherRestrictions</xsl:text></xsl:attribute>
			</xsl:if>
		</RestrictCd>
	</xsl:template>
	<xsl:template match="ScopeCd">
		<ScopeCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>attribute</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>attributeType</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>collectionHardware</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>collectionSession</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>dataset</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>series</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=007">
				<xsl:attribute name="value"><xsl:text>nonGeographicDataset</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=008">
				<xsl:attribute name="value"><xsl:text>dimensionGroup</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=009">
				<xsl:attribute name="value"><xsl:text>feature</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=010">
				<xsl:attribute name="value"><xsl:text>featureType</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=011">
				<xsl:attribute name="value"><xsl:text>propertyType</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=012">
				<xsl:attribute name="value"><xsl:text>fieldSession</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=013">
				<xsl:attribute name="value"><xsl:text>software</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=014">
				<xsl:attribute name="value"><xsl:text>service</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=015">
				<xsl:attribute name="value"><xsl:text>model</xsl:text></xsl:attribute>
			</xsl:if>
		</ScopeCd>
	</xsl:template>
	<xsl:template match="SpatRepTypCd">
		<SpatRepTypCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>vector</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>grid</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>textTable</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>tin</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>stereoModel</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>video</xsl:text></xsl:attribute>
			</xsl:if>
		</SpatRepTypCd>
	</xsl:template>
	<xsl:template match="TopicCatCd">
		<TopicCatCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>farming</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>biota</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>boundaries</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>climatologyMeteorologyAtmosphere</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>economy</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>elevation</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=007">
				<xsl:attribute name="value"><xsl:text>environment</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=008">
				<xsl:attribute name="value"><xsl:text>geoscientificInformation</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=009">
				<xsl:attribute name="value"><xsl:text>health</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=010">
				<xsl:attribute name="value"><xsl:text>imageryBaseMapsEarthCover</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=011">
				<xsl:attribute name="value"><xsl:text>intelligenceMilitary</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=012">
				<xsl:attribute name="value"><xsl:text>inlandWaters</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=013">
				<xsl:attribute name="value"><xsl:text>location</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=014">
				<xsl:attribute name="value"><xsl:text>oceans</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=015">
				<xsl:attribute name="value"><xsl:text>planningCadastre</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=016">
				<xsl:attribute name="value"><xsl:text>society</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=017">
				<xsl:attribute name="value"><xsl:text>structure</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=018">
				<xsl:attribute name="value"><xsl:text>transportation</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=019">
				<xsl:attribute name="value"><xsl:text>utilitiesCommunication</xsl:text></xsl:attribute>
			</xsl:if>
		</TopicCatCd>
	</xsl:template>
	<xsl:template match="TopoLevCd">
		<TopoLevCd>
			<xsl:if test="@value=001">
				<xsl:attribute name="value"><xsl:text>geometryOnly</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=002">
				<xsl:attribute name="value"><xsl:text>topology1D</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=003">
				<xsl:attribute name="value"><xsl:text>planarGraph</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=004">
				<xsl:attribute name="value"><xsl:text>fullPlanarGraph</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=005">
				<xsl:attribute name="value"><xsl:text>surfaceGraph</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=006">
				<xsl:attribute name="value"><xsl:text>fullSurfaceGraph</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=007">
				<xsl:attribute name="value"><xsl:text>topology3D</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=008">
				<xsl:attribute name="value"><xsl:text>fullTopology3D</xsl:text></xsl:attribute>
			</xsl:if>
			<xsl:if test="@value=009">
				<xsl:attribute name="value"><xsl:text>abstract</xsl:text></xsl:attribute>
			</xsl:if>
		</TopoLevCd>
	</xsl:template>

  <xsl:template match="*">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>
  
  <xsl:template match="@*|text()|comment()|processing-instruction">
    <xsl:copy-of select="."/>
  </xsl:template>
</xsl:stylesheet>
